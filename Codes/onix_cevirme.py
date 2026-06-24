import keras
import keras2onnx

# Modeli yükle
model = keras.models.load_model("corn_disease_cnn_model.h5")

# ONNX formatına çevir
onnx_model = keras2onnx.convert_keras(model, model.name)

# Kaydet
import onnx
onnx.save_model(onnx_model, "model.onnx")
