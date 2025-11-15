# ⚡ AWS Configure - Quick Command Guide

**5-minute setup for AWS CLI**

---

## 🎯 Step-by-Step Commands

### 1. Install AWS CLI (macOS)

```bash
# Check if already installed
aws --version

# If not installed:
brew install awscli

# Verify
aws --version
```

---

### 2. Get Your AWS Access Keys

**Go to AWS Console** → https://console.aws.amazon.com/

```
1. Search for "IAM" in the top search bar
2. Click "Users" (left sidebar)
3. Click "Create user"
4. Username: "signum-deploy-user"
5. Click "Next"
6. Select "Attach policies directly"
7. Add policies:
   ✅ AmazonEC2FullAccess
   ✅ AmazonS3FullAccess
8. Click "Next" → "Create user"
9. Click on the new user
10. Go to "Security credentials" tab
11. Click "Create access key"
12. Select "Command Line Interface (CLI)"
13. Check "I understand" → "Next"
14. Click "Create access key"
15. 🔴 SAVE BOTH KEYS NOW! (shown only once)
```

**You'll get**:
```
Access key ID:     AKIAIOSFODNN7EXAMPLE (20 chars)
Secret access key: wJalrXUt...EXAMPLEKEY (40 chars)
```

---

### 3. Configure AWS CLI

```bash
aws configure
```

**Enter when prompted**:
```
AWS Access Key ID [None]: <paste your 20-char key>
AWS Secret Access Key [None]: <paste your 40-char key>
Default region name [None]: us-east-1
Default output format [None]: json
```

---

### 4. Verify Setup

```bash
# Test 1: Check configuration
aws configure list

# Test 2: Get your AWS identity
aws sts get-caller-identity

# Test 3: List S3 buckets
aws s3 ls
```

**If all 3 work without errors** ✅ **You're configured!**

---

## 🚀 Now Deploy SIGNUM

### Upload Data to S3

```bash
# Create bucket
aws s3 mb s3://signum-hospital-data --region us-east-1

# Upload your dataset
cd /Users/harshmaheshwari/development/Signum_1
aws s3 sync hospitals_current_data/ s3://signum-hospital-data/hospitals_current_data/

# Verify (should show ~40 files)
aws s3 ls s3://signum-hospital-data/hospitals_current_data/ --recursive | wc -l
```

---

## 🔧 Useful Commands

```bash
# View credentials (redacted)
cat ~/.aws/credentials

# Change region
aws configure set region us-west-2

# Test S3 access
aws s3 ls

# Test EC2 access
aws ec2 describe-instances

# Get account ID
aws sts get-caller-identity --query Account --output text
```

---

## 🐛 Troubleshooting

### "Unable to locate credentials"
```bash
# Re-run configure
aws configure
```

### "Access Denied"
```bash
# Check your IAM permissions in AWS Console
# Ensure user has EC2 and S3 policies attached
```

### "Invalid credentials"
```bash
# Keys might be wrong - regenerate in AWS Console
# Delete old key, create new, run aws configure again
```

---

## ⏱️ Time Required

- **Install AWS CLI**: 2 minutes
- **Create IAM user & keys**: 5 minutes
- **Configure CLI**: 1 minute
- **Test & verify**: 2 minutes
- **Total**: ~10 minutes

---

## ✅ Success Checklist

- [ ] `aws --version` shows version 2.x
- [ ] `aws sts get-caller-identity` returns your account
- [ ] `aws s3 ls` works (may be empty)
- [ ] Keys saved securely

---

**Ready?** → See [QUICK_START_AWS.md](QUICK_START_AWS.md) for full deployment!

*Last Updated: November 2025*
