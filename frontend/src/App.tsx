import React, { useState } from 'react';
import './App.css';
import { UploadOutlined, LoadingOutlined } from '@ant-design/icons';
import {
  Upload,
  Button,
  Card,
  Typography,
  Divider,
  List,
  Statistic,
  Row,
  Col,
  message,
} from 'antd';
import type { RcFile, UploadFile, UploadProps } from 'antd/es/upload/interface';

const { Title, Text, Paragraph } = Typography;

interface NutritionInfo {
  name: string;
  calories: number;
  protein: number;
  carbs: number;
  fats: number;
  error?: string;
}

interface AnalysisResult {
  detected_food: string[];
  main_ingredient: string;
  nutrition_info: NutritionInfo;
  healthier_alternative: string;
}

const App: React.FC = () => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState<boolean>(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const MAX_FILE_SIZE_MB = 4;

  const props: UploadProps = {
    onRemove: () => {
      setFileList([]);
      setImageUrl(null);
      setError(null);
    },
    beforeUpload: (file: RcFile) => {
      const isJpgOrPng = file.type === 'image/jpeg' || file.type === 'image/png';
      if (!isJpgOrPng) {
        message.error('You can only upload JPG/PNG file!');
        return Upload.LIST_IGNORE;
      }

      const isUnderSizeLimit = file.size / 1024 / 1024 < MAX_FILE_SIZE_MB;
      if (!isUnderSizeLimit) {
        message.error(`Image must be smaller than ${MAX_FILE_SIZE_MB}MB for serverless functions!`);
        return Upload.LIST_IGNORE;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        setImageUrl(e.target?.result as string);
      };
      reader.readAsDataURL(file);

      setFileList([
        {
          uid: file.uid,
          name: file.name,
          status: 'done',
          url: URL.createObjectURL(file),
          originFileObj: file,
        },
      ]);

      setError(null);
      return Upload.LIST_IGNORE;
    },
    fileList,
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.error('Please select an image first!');
      return;
    }

    const formData = new FormData();
    const file = fileList[0];

    if (file.originFileObj instanceof Blob) {
      formData.append('image', file.originFileObj);
    } else {
      message.error('Invalid file object');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let errorMessage;
        try {
          const errorData = await response.json();
          errorMessage = errorData.message || errorData.error || `Error ${response.status}`;
        } catch (e) {
          errorMessage = `Error ${response.status}`;
        }
        throw new Error(errorMessage);
      }

      const data: AnalysisResult = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message);
      setResult(null);
    } finally {
      setUploading(false);
    }
  };

  const uploadButton = (
    <div>
      {uploading ? <LoadingOutlined /> : <UploadOutlined />}
      <div style={{ marginTop: 8 }}>Upload</div>
    </div>
  );

  return (
    <div className="app-container">
      <Title level={2}>AI Calorie Counter</Title>
      <Paragraph>Upload a food image to get nutritional information and healthier alternatives.</Paragraph>

      <div className="upload-section">
        <Upload listType="picture-card" {...props}>
          {fileList.length >= 1 ? null : uploadButton}
        </Upload>
        <Button
          type="primary"
          onClick={handleUpload}
          disabled={fileList.length === 0}
          loading={uploading}
          style={{ marginTop: 16 }}
        >
          {uploading ? 'Analyzing...' : 'Analyze Food'}
        </Button>
      </div>

      {error && (
        <div className="error-section" style={{ marginTop: 16 }}>
          <Card bordered={false} style={{ backgroundColor: '#fff2f0' }}>
            <Text type="danger" strong>Error: {error}</Text>
            <Paragraph type="secondary" style={{ marginTop: 8 }}>
              Please try again with a different image or contact support if the issue persists.
            </Paragraph>
          </Card>
        </div>
      )}

      {result && (
        <div className="results-section">
          <Divider />
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Card title="Food Analysis Results" bordered={false}>
                <div className="result-item">
                  <Title level={4}>Detected Foods</Title>
                  <List
                    size="small"
                    bordered
                    dataSource={result.detected_food}
                    renderItem={(item) => <List.Item>{item}</List.Item>}
                  />
                </div>

                <div className="result-item">
                  <Title level={4}>Main Ingredient</Title>
                  <Text strong>{result.main_ingredient}</Text>
                </div>

                {result.nutrition_info.error ? (
                  <div className="result-item">
                    <Text type="danger">{result.nutrition_info.error}</Text>
                  </div>
                ) : (
                  <div className="result-item">
                    <Title level={4}>Nutrition Information</Title>
                    <Text>{result.nutrition_info.name}</Text>
                    <Row gutter={16} style={{ marginTop: 16 }}>
                      <Col span={6}>
                        <Statistic title="Calories" value={result.nutrition_info.calories} suffix="kcal" />
                      </Col>
                      <Col span={6}>
                        <Statistic title="Protein" value={result.nutrition_info.protein} suffix="g" />
                      </Col>
                      <Col span={6}>
                        <Statistic title="Carbs" value={result.nutrition_info.carbs} suffix="g" />
                      </Col>
                      <Col span={6}>
                        <Statistic title="Fats" value={result.nutrition_info.fats} suffix="g" />
                      </Col>
                    </Row>
                  </div>
                )}
              </Card>
            </Col>

            <Col xs={24} md={12}>
              <Card title="Healthier Alternative" bordered={false}>
                <Paragraph>{result.healthier_alternative}</Paragraph>
              </Card>

              {imageUrl && (
                <Card title="Your Food Image" bordered={false} style={{ marginTop: 16 }}>
                  <img src={imageUrl} alt="Food" style={{ width: '100%', objectFit: 'contain' }} />
                </Card>
              )}
            </Col>
          </Row>
        </div>
      )}
    </div>
  );
};

export default App;
