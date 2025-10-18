<template>
  <div>
    <el-steps :active="step" finish-status="success">
      <el-step title="上传 DICOM ZIP" />
      <el-step title="处理数据" />
      <el-step title="查看结果" />
    </el-steps>
    <div v-if="step === 0">
      <el-form>
        <el-input v-model="patient_name" placeholder="病人姓名" />
        <el-input v-model="study_date" placeholder="检查日期" />
        <input type="file" ref="fileInput" @change="handleFile" />
        <el-button type="primary" @click="uploadZip" :loading="uploading"
          >上传</el-button
        >
      </el-form>
    </div>
    <div v-else-if="step === 1">
      <el-button type="primary" @click="processCase" :loading="processing"
        >开始处理</el-button
      >
    </div>
    <div v-else-if="step === 2">
      <el-button type="primary" @click="viewResult">查看结果</el-button>
    </div>
  </div>
</template>

<script>
import { uploadDicomZip, processCase, BASE_URL } from '../api.js';
export default {
  data() {
    return {
      patient_name: "",
      study_date: "",
      file: null,
      uploading: false,
      processing: false,
      step: 0,
    };
  },
  methods: {
    handleFile(e) {
      this.file = e.target.files[0];
    },
    async uploadZip() {
      if (!this.patient_name || !this.study_date || !this.file) return;
      this.uploading = true;
      try {
        await uploadDicomZip({
          patient_name: this.patient_name,
          study_date: this.study_date,
          file: this.file
        });
        this.$message.success("上传成功");
        this.step = 1;
      } catch (e) {
        this.$message.error("上传失败");
      } finally {
        this.uploading = false;
      }
    },
    async processCase() {
      this.processing = true;
      try {
        await processCase(this.patient_name, this.study_date);
        this.$message.success("处理完成");
        this.step = 2;
      } catch (e) {
        this.$message.error("处理失败");
      } finally {
        this.processing = false;
      }
    },
    viewResult() {
      this.$router.push(`/results/${this.patient_name}/${this.study_date}`);
    },
  },
};
</script>