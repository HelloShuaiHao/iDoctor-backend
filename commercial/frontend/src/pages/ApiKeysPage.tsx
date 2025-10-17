import { type FC, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { authService } from '@/services/authService';
import { useAuth } from '@/context/AuthContext';
import { ROUTES } from '@/utils/constants';
import type { APIKey, CreateAPIKeyRequest } from '@/types/auth';
import {
  Key,
  Plus,
  Copy,
  Trash2,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertCircle,
  Calendar,
  Eye,
  EyeOff,
} from 'lucide-react';

const ApiKeysPage: FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create dialog state
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createForm, setCreateForm] = useState<CreateAPIKeyRequest>({
    name: '',
    expires_at: undefined,
  });

  // New key display state
  const [newKey, setNewKey] = useState<APIKey | null>(null);
  const [showNewKeyDialog, setShowNewKeyDialog] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [keyVisible, setKeyVisible] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate(ROUTES.LOGIN);
      return;
    }
    loadAPIKeys();
  }, [isAuthenticated, navigate]);

  const loadAPIKeys = async () => {
    try {
      setLoading(true);
      setError(null);
      const keys = await authService.getAPIKeys();
      setApiKeys(keys);
    } catch (err: any) {
      console.error('Failed to load API keys:', err);
      setError('加载 API 密钥失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async () => {
    if (!createForm.name.trim()) {
      setError('请输入密钥名称');
      return;
    }

    try {
      setCreateLoading(true);
      setError(null);

      const newApiKey = await authService.createAPIKey({
        name: createForm.name.trim(),
        expires_at: createForm.expires_at || undefined,
      });

      // Show the new key in a dialog
      setNewKey(newApiKey);
      setShowNewKeyDialog(true);
      setShowCreateDialog(false);

      // Reset form
      setCreateForm({ name: '', expires_at: undefined });

      // Reload keys
      await loadAPIKeys();
    } catch (err: any) {
      console.error('Failed to create API key:', err);
      setError(err.response?.data?.detail || '创建 API 密钥失败');
    } finally {
      setCreateLoading(false);
    }
  };

  const handleCopyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handleDeleteKey = async (keyId: string, keyName: string) => {
    if (!confirm(`确定要删除密钥 "${keyName}" 吗？此操作不可撤销。`)) {
      return;
    }

    try {
      await authService.deleteAPIKey(keyId);
      await loadAPIKeys();
    } catch (err: any) {
      console.error('Failed to delete API key:', err);
      setError(err.response?.data?.detail || '删除 API 密钥失败');
    }
  };

  const handleDeactivateKey = async (keyId: string, keyName: string) => {
    if (!confirm(`确定要停用密钥 "${keyName}" 吗？`)) {
      return;
    }

    try {
      await authService.deactivateAPIKey(keyId);
      await loadAPIKeys();
    } catch (err: any) {
      console.error('Failed to deactivate API key:', err);
      setError(err.response?.data?.detail || '停用 API 密钥失败');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const isExpired = (expiresAt?: string) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  return (
    <MainLayout>
      <div className="container mx-auto px-4 py-12 max-w-6xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">API 密钥管理</h1>
            <p className="text-muted-foreground">
              创建和管理您的 API 访问密钥
            </p>
          </div>
          <Button onClick={() => setShowCreateDialog(true)} size="lg">
            <Plus className="h-4 w-4 mr-2" />
            创建新密钥
          </Button>
        </div>

        {/* Security Warning */}
        <Alert className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            请妥善保管您的 API 密钥。密钥仅在创建时显示一次，之后无法再次查看完整密钥。如果您丢失了密钥，需要创建新的密钥。
          </AlertDescription>
        </Alert>

        {/* Error Display */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* API Keys List */}
        {loading ? (
          <Card>
            <CardContent className="py-12">
              <div className="flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="ml-3 text-muted-foreground">加载中...</span>
              </div>
            </CardContent>
          </Card>
        ) : apiKeys.length === 0 ? (
          <Card className="border-2 border-dashed">
            <CardContent className="py-12">
              <div className="text-center space-y-4">
                <div className="w-20 h-20 rounded-full bg-muted mx-auto flex items-center justify-center">
                  <Key className="h-10 w-10 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold mb-2">暂无 API 密钥</h3>
                  <p className="text-muted-foreground mb-6">
                    创建您的第一个 API 密钥以开始使用 API
                  </p>
                </div>
                <Button onClick={() => setShowCreateDialog(true)} size="lg">
                  <Plus className="h-4 w-4 mr-2" />
                  创建 API 密钥
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {apiKeys.map((apiKey) => {
              const expired = isExpired(apiKey.expires_at);
              return (
                <Card key={apiKey.id} className={expired ? 'opacity-60' : ''}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                          <Key className="h-5 w-5 text-white" />
                        </div>
                        <div>
                          <CardTitle className="text-lg">{apiKey.name}</CardTitle>
                          <CardDescription className="mt-1">
                            <code className="text-xs bg-muted px-2 py-1 rounded">
                              {apiKey.key_prefix}...
                            </code>
                          </CardDescription>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {expired ? (
                          <Badge variant="destructive">
                            <XCircle className="h-3 w-3 mr-1" />
                            已过期
                          </Badge>
                        ) : apiKey.is_active ? (
                          <Badge className="bg-green-500">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            激活中
                          </Badge>
                        ) : (
                          <Badge variant="outline">
                            <XCircle className="h-3 w-3 mr-1" />
                            已停用
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid md:grid-cols-2 gap-4 mb-4">
                      <div>
                        <p className="text-sm text-muted-foreground mb-1">创建时间</p>
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm font-medium">
                            {formatDate(apiKey.created_at)}
                          </span>
                        </div>
                      </div>

                      {apiKey.expires_at && (
                        <div>
                          <p className="text-sm text-muted-foreground mb-1">过期时间</p>
                          <div className="flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-muted-foreground" />
                            <span className={`text-sm font-medium ${expired ? 'text-destructive' : ''}`}>
                              {formatDate(apiKey.expires_at)}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="flex gap-2">
                      {apiKey.is_active && !expired && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeactivateKey(apiKey.id, apiKey.name)}
                        >
                          停用
                        </Button>
                      )}
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDeleteKey(apiKey.id, apiKey.name)}
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        删除
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Create Dialog */}
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>创建新的 API 密钥</DialogTitle>
              <DialogDescription>
                为您的应用程序创建一个新的 API 密钥。密钥将仅显示一次。
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="key-name">密钥名称 *</Label>
                <Input
                  id="key-name"
                  placeholder="例如：生产环境密钥"
                  value={createForm.name}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, name: e.target.value })
                  }
                  disabled={createLoading}
                />
                <p className="text-xs text-muted-foreground">
                  给密钥起一个有意义的名称，方便识别用途
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="expires-at">过期时间（可选）</Label>
                <Input
                  id="expires-at"
                  type="datetime-local"
                  value={createForm.expires_at || ''}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, expires_at: e.target.value })
                  }
                  disabled={createLoading}
                />
                <p className="text-xs text-muted-foreground">
                  留空表示永不过期
                </p>
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowCreateDialog(false)}
                disabled={createLoading}
              >
                取消
              </Button>
              <Button onClick={handleCreateKey} disabled={createLoading}>
                {createLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    创建中...
                  </>
                ) : (
                  '创建密钥'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* New Key Display Dialog */}
        <Dialog open={showNewKeyDialog} onOpenChange={setShowNewKeyDialog}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>API 密钥创建成功</DialogTitle>
              <DialogDescription>
                请立即复制并保存您的 API 密钥。出于安全考虑，此密钥将仅显示一次。
              </DialogDescription>
            </DialogHeader>

            {newKey && (
              <div className="space-y-4 py-4">
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    请将此密钥保存在安全的地方。关闭此对话框后，您将无法再次查看完整密钥。
                  </AlertDescription>
                </Alert>

                <div className="space-y-2">
                  <Label>密钥名称</Label>
                  <p className="font-medium">{newKey.name}</p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>API 密钥</Label>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setKeyVisible(!keyVisible)}
                    >
                      {keyVisible ? (
                        <>
                          <EyeOff className="h-4 w-4 mr-2" />
                          隐藏
                        </>
                      ) : (
                        <>
                          <Eye className="h-4 w-4 mr-2" />
                          显示
                        </>
                      )}
                    </Button>
                  </div>
                  <div className="relative">
                    <Input
                      readOnly
                      type={keyVisible ? 'text' : 'password'}
                      value={newKey.key || ''}
                      className="font-mono pr-24"
                    />
                    <Button
                      size="sm"
                      className="absolute right-1 top-1 h-8"
                      onClick={() => handleCopyKey(newKey.key || '')}
                    >
                      {copiedKey ? (
                        <>
                          <CheckCircle2 className="h-4 w-4 mr-2" />
                          已复制
                        </>
                      ) : (
                        <>
                          <Copy className="h-4 w-4 mr-2" />
                          复制
                        </>
                      )}
                    </Button>
                  </div>
                </div>

                <div className="bg-muted/50 rounded-lg p-4 text-sm">
                  <h4 className="font-semibold mb-2">使用示例</h4>
                  <pre className="text-xs overflow-x-auto">
{`# 在请求头中使用 API 密钥
curl -H "X-API-Key: ${newKey.key || 'YOUR_API_KEY'}" \\
  https://api.idoctor.com/v1/endpoint`}
                  </pre>
                </div>
              </div>
            )}

            <DialogFooter>
              <Button
                onClick={() => {
                  setShowNewKeyDialog(false);
                  setNewKey(null);
                  setKeyVisible(false);
                  setCopiedKey(false);
                }}
              >
                我已保存密钥
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Usage Guide */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>如何使用 API 密钥</CardTitle>
            <CardDescription>
              在您的应用程序中集成 iDoctor API
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-semibold mb-2">1. 在请求头中添加密钥</h4>
              <pre className="bg-muted p-3 rounded text-xs overflow-x-auto">
{`X-API-Key: your_api_key_here`}
              </pre>
            </div>

            <div>
              <h4 className="font-semibold mb-2">2. 示例请求（Python）</h4>
              <pre className="bg-muted p-3 rounded text-xs overflow-x-auto">
{`import requests

headers = {
    "X-API-Key": "your_api_key_here",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://api.idoctor.com/v1/analyze",
    headers=headers,
    json={"data": "..."}
)

print(response.json())`}
              </pre>
            </div>

            <div>
              <h4 className="font-semibold mb-2">3. 示例请求（JavaScript）</h4>
              <pre className="bg-muted p-3 rounded text-xs overflow-x-auto">
{`fetch('https://api.idoctor.com/v1/analyze', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your_api_key_here',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ data: '...' })
})
  .then(response => response.json())
  .then(data => console.log(data));`}
              </pre>
            </div>

            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <strong>安全提示：</strong> 不要在客户端代码中暴露您的 API 密钥。始终在服务器端使用密钥。
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
};

export default ApiKeysPage;
