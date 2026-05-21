# Cloud Server Tool

Optional Flask file service used by the WPF cloud window during local testing.

```powershell
pip install -r tools/cloud-server/requirements.txt
python tools/cloud-server/train_server.py --port 9527
```

Uploaded files are stored in `cloud_storage/`, which is ignored by git.
