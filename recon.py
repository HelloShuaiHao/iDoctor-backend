import os
import numpy as np
import cv2

class CT3DReconstructor:
    def __init__(self, target_mask, output_dir=None, spacing=None):
        """
        初始化3D重建器（仅处理目标区域）
        """
        self.target_mask = target_mask
        self.output_dir = output_dir or "ct_3d_reconstruction"
        os.makedirs(self.output_dir, exist_ok=True)
        self.spacing = spacing or (1.0, 1.0, 1.0)
        self.target_mesh = None
        self.volume_info = None
        print("CT3DReconstructor 初始化完成（仅目标区域模式）")

    def _create_mesh_from_mask(self, mask, level=0.5, fill_holes=True, hole_size=300.0, smooth=True, smooth_iterations=50):
        """
        从掩码创建3D网格（兼容 scikit-image 0.25+，防止重建空洞）

        参数:
            mask: 3D二值掩码
            level: marching cubes阈值
            fill_holes: 是否填充孔洞
            hole_size: 孔洞填充大小
            smooth: 是否进行平滑处理
            smooth_iterations: 平滑迭代次数(建议20-100)
        """
        from skimage import measure
        import vtk, numpy as np

        if np.count_nonzero(mask) == 0:
            raise ValueError("Mask为空，无法重建")

        # ✅ 关键修改：在新版 marching_cubes 下，pad 一层边界体素
        # 这样可以防止算法在边缘或内部零值处误判为"空气"，导致大孔
        mask = np.pad(mask, pad_width=1, mode='constant', constant_values=0)
        mask = (mask > 0).astype(np.float32)

        # ✅ 保持原有 level 参数
        vertices, faces, _, _ = measure.marching_cubes(
            mask,
            level=level,
            spacing=self.spacing
        )

        # === 以下部分完全保持原样 ===
        vtk_points = vtk.vtkPoints()
        for v in vertices:
            vtk_points.InsertNextPoint(v)

        vtk_triangles = vtk.vtkCellArray()
        for f in faces:
            tri = vtk.vtkTriangle()
            tri.GetPointIds().SetId(0, int(f[0]))
            tri.GetPointIds().SetId(1, int(f[1]))
            tri.GetPointIds().SetId(2, int(f[2]))
            vtk_triangles.InsertNextCell(tri)

        mesh = vtk.vtkPolyData()
        mesh.SetPoints(vtk_points)
        mesh.SetPolys(vtk_triangles)

        # 1. 填充孔洞
        if fill_holes and hole_size > 0:
            hole_filler = vtk.vtkFillHolesFilter()
            hole_filler.SetInputData(mesh)
            hole_filler.SetHoleSize(hole_size)
            hole_filler.Update()
            mesh = hole_filler.GetOutput()

        # 2. 平滑处理 - 解决锯齿状表面问题
        if smooth and smooth_iterations > 0:
            smoother = vtk.vtkSmoothPolyDataFilter()
            smoother.SetInputData(mesh)
            smoother.SetNumberOfIterations(smooth_iterations)
            smoother.SetRelaxationFactor(0.1)  # 控制平滑强度(0-1)
            smoother.FeatureEdgeSmoothingOff()  # 保留特征边缘
            smoother.BoundarySmoothingOn()     # 边界也平滑
            smoother.Update()
            mesh = smoother.GetOutput()
            print(f"✅ 平滑处理完成 (迭代{smooth_iterations}次)")

        return mesh

    def create_target_mesh(self, level=0.5, hole_size=300.0, format='stl', model_name='target_mesh',
                          smooth=True, smooth_iterations=50, subdivide=False, subdivide_iterations=2,
                          decimate=False, target_reduction=0.5):
        """
        只创建目标区域网格

        参数:
            level: Marching Cubes 阈值
            hole_size: 孔洞填充大小
            format: 输出格式 ('stl' 或 'obj')
            model_name: 模型文件名（不含扩展名）
            smooth: 是否平滑处理
            smooth_iterations: 平滑迭代次数
            subdivide: 是否进行网格细分(提高表面质量)
            subdivide_iterations: 细分迭代次数
            decimate: 是否进行网格抽取(减少三角形数量)
            target_reduction: 抽取目标比例(0-1, 如0.5表示减少50%的三角形)

        返回:
            str: 保存的文件路径
        """
        print("正在创建目标区域3D网格...")
        self.target_mesh = self._create_mesh_from_mask(
            self.target_mask,
            level=level,
            hole_size=hole_size,
            smooth=smooth,
            smooth_iterations=smooth_iterations
        )

        # 可选：网格细分 - 提高表面分辨率
        if subdivide and subdivide_iterations > 0:
            import vtk
            subdivider = vtk.vtkLinearSubdivisionFilter()
            subdivider.SetInputData(self.target_mesh)
            subdivider.SetNumberOfSubdivisions(subdivide_iterations)
            subdivider.Update()
            self.target_mesh = subdivider.GetOutput()
            print(f"✅ 网格细分完成 ({subdivide_iterations}次迭代)")

        # 可选：网格抽取 - 减少三角形数量同时保持形状
        if decimate and 0 < target_reduction < 1:
            import vtk
            decimator = vtk.vtkDecimatePro()
            decimator.SetInputData(self.target_mesh)
            decimator.SetTargetReduction(target_reduction)
            decimator.PreserveTopologyOn()  # 保持拓扑结构
            decimator.Update()
            self.target_mesh = decimator.GetOutput()
            print(f"✅ 网格抽取完成 (减少{target_reduction*100:.0f}%三角形)")

        filename = f"{model_name}.{format.lower()}"
        filepath = self._save_mesh(self.target_mesh, filename)
        print("✅ 目标区域网格创建完成！")
        return filepath

    def _save_mesh(self, mesh, filename):
        """保存mesh为OBJ/STL文件"""
        import vtk, os
        filepath = os.path.join(self.output_dir, filename)

        # 根据文件扩展名选择不同的writer
        if filename.lower().endswith('.stl'):
            writer = vtk.vtkSTLWriter()
        elif filename.lower().endswith('.obj'):
            writer = vtk.vtkOBJWriter()
        else:
            raise ValueError(f"不支持的文件格式: {filename}，仅支持 .obj 和 .stl")

        writer.SetFileName(filepath)
        writer.SetInputData(mesh)
        writer.Write()
        print(f"💾 已保存: {filename}")
        return filepath

    def compute_volume(self):
        """
        根据掩码体素数量计算总体积（mm³）
        返回:
            float : 目标区域总体积 (mm³)
        """
        dx, dy, dz = self.spacing
        voxel_volume_mm3 = dx * dy * dz
        voxel_count = int((self.target_mask > 0).sum())

        volume_mm3 = voxel_count * voxel_volume_mm3
        volume_ml = volume_mm3 / 1000.0

        print(f"📏 体积计算完成：{volume_mm3:.2f} mm³ ≈ {volume_ml:.2f} mL")
        return volume_mm3

    def visualize_target(self):
        """简单可视化目标区域"""
        import vtk
        if self.target_mesh is None:
            raise ValueError("请先调用 create_target_mesh()")

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(self.target_mesh)
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1, 0, 0)
        actor.GetProperty().SetOpacity(1.0)

        renderer = vtk.vtkRenderer()
        renderer.AddActor(actor)
        renderer.SetBackground(0.1, 0.1, 0.1)

        window = vtk.vtkRenderWindow()
        window.AddRenderer(renderer)
        interactor = vtk.vtkRenderWindowInteractor()
        interactor.SetRenderWindow(window)
        window.Render()
        interactor.Start()

# 输入：目标区域的二值掩码目录，输出目录，体素间距
# def main():
#     import os
#     import cv2
#     import numpy as np

#     # 1️⃣ 输入：目标区域的二值掩码目录
#     mask_dir = "D:/Med/1006results/rresults16285041/full_mask255"  # 存放二值mask的文件夹
#     output_dir = "D:/Med/1006results/rresults16285041/full_mask255_recon"  # 输出目录
#     os.makedirs(output_dir, exist_ok=True)

#     # 2️⃣ 读取所有mask切片并堆叠成3D体数据
#     mask_files = sorted([f for f in os.listdir(mask_dir) if f.endswith(".png")])
#     if not mask_files:
#         raise ValueError(f"未找到mask文件: {mask_dir}")

#     mask_volume = []
#     for f in mask_files:
#         img = cv2.imread(os.path.join(mask_dir, f), cv2.IMREAD_GRAYSCALE)
#         img = (img > 0).astype(np.float32)  # 转为0/1
#         mask_volume.append(img)
#     mask_volume = np.stack(mask_volume, axis=0)

#     print(f"✅ Mask volume shape: {mask_volume.shape}, nonzero voxels: {np.count_nonzero(mask_volume)}")

#     # 3️⃣ 初始化3D重建器（只用mask）
#     reconstructor = CT3DReconstructor(
#         target_mask=mask_volume,
#         output_dir=output_dir,
#         spacing=(1.0, 1.0, 1.0)       # 若有真实CT spacing，可以改
#     )

#     # 4️⃣ 只重建目标区域网格
#     reconstructor.create_target_mesh(level=0.5, hole_size=300.0)

#     # 计算体积
#     volume_info = reconstructor.compute_volume()
#     print(volume_info)

#     # 5️⃣ 可选：3D 可视化
#     reconstructor.visualize_target()

# if __name__ == "__main__":
#     main()

# reconstruct_ct_volume
def reconstruct_ct_volume(mask_dir, output_dir, spacing, visualize=False, format='stl', model_name='target_mesh',
                         smooth=True, smooth_iterations=50, subdivide=False, subdivide_iterations=2,
                         decimate=False, target_reduction=0.5):
    """
    对目标区域的二值掩码进行三维重建并计算体积

    参数:
        mask_dir : str
            存放二值掩码 (0/1或0/255) 的文件夹路径，每个切片一张png图。
        output_dir : str
            输出结果保存路径（包含OBJ/STL文件与日志）。
        spacing : tuple(float)
            (dx, dy, dz)，即体素间距，单位为毫米(mm)。
        visualize : bool
            是否在重建完成后进行3D可视化（默认False）。
        format : str
            输出格式 ('stl' 或 'obj')，默认 'stl'
        model_name : str
            模型文件名（不含扩展名），默认 'target_mesh'
        smooth : bool
            是否进行平滑处理（默认True）
        smooth_iterations : int
            平滑迭代次数，建议20-100（默认50）
        subdivide : bool
            是否进行网格细分以提高表面质量（默认False）
        subdivide_iterations : int
            细分迭代次数（默认2）
        decimate : bool
            是否进行网格抽取以减少三角形数量（默认False）
        target_reduction : float
            抽取目标比例(0-1)，如0.5表示减少50%的三角形（默认0.5）

    返回:
        dict : 包含体积信息和模型路径
            {
                'volume_mm3': float,
                'volume_ml': float,
                'model_path': str,
                'voxel_count': int
            }
    """
    # 1️⃣ 检查输入目录
    if not os.path.exists(mask_dir):
        raise FileNotFoundError(f"掩码目录不存在: {mask_dir}")
    os.makedirs(output_dir, exist_ok=True)

    # 2️⃣ 读取所有mask切片并堆叠成3D体数据
    mask_files = sorted([f for f in os.listdir(mask_dir) if f.lower().endswith(".png")])
    if not mask_files:
        raise ValueError(f"未找到mask文件: {mask_dir}")

    mask_volume = []
    for f in mask_files:
        img = cv2.imread(os.path.join(mask_dir, f), cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"⚠️ 跳过无法读取的文件: {f}")
            continue
        img = (img > 0).astype(np.float32)
        mask_volume.append(img)

    mask_volume = np.stack(mask_volume, axis=0)
    print(f"✅ Mask volume shape: {mask_volume.shape}, nonzero voxels: {np.count_nonzero(mask_volume)}")

    # 3️⃣ 初始化3D重建器
    reconstructor = CT3DReconstructor(
        target_mask=mask_volume,
        output_dir=output_dir,
        spacing=spacing
    )

    # 4️⃣ 生成3D网格（添加平滑、细分和抽取选项）
    model_path = reconstructor.create_target_mesh(
        level=0.5,
        hole_size=300.0,
        format=format,
        model_name=model_name,
        smooth=smooth,
        smooth_iterations=smooth_iterations,
        subdivide=subdivide,
        subdivide_iterations=subdivide_iterations,
        decimate=decimate,
        target_reduction=target_reduction
    )

    # 5️⃣ 计算体积
    volume_mm3 = reconstructor.compute_volume()
    volume_ml = volume_mm3 / 1000.0
    voxel_count = int((mask_volume > 0).sum())

    print(f"📏 Volume info: {volume_mm3} mm³ = {volume_ml} mL")

    # 6️⃣ 可选：3D可视化
    if visualize:
        reconstructor.visualize_target()

    return {
        'volume_mm3': float(volume_mm3),
        'volume_ml': float(volume_ml),
        'model_path': model_path,
        'voxel_count': voxel_count,
        'spacing': spacing
    }

# if __name__ == "__main__":
#     mask_dir = "recon_19392963/full_255mask"  # 存放二值mask的文件夹
#     output_dir = "recon_19392963/full_255masknnnnn"  # 输出目录
#     spacing = (0.734375, 0.734375, 3.0)
#     main(mask_dir, output_dir, spacing, visualize=True)




def convert_binary_to_255(input_dir, output_dir):
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"输入文件夹不存在: {input_dir}")
    os.makedirs(output_dir, exist_ok=True)

    processed_files = []

    for filename in os.listdir(input_dir):
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tif")):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)

            img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                print(f"⚠️ 无法读取：{input_path}")
                continue

            img_255 = (img > 0).astype(np.uint8) * 255

            cv2.imwrite(output_path, img_255)
            processed_files.append(filename)
            print(f"✅ 已处理：{filename}")
    return processed_files