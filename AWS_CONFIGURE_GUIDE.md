# 🔐 AWS Configuration Guide

Complete guide to setting up AWS CLI credentials for SIGNUM deployment.

---

## 📋 Prerequisites

- AWS Account created
- AWS CLI installed on your Mac

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Install AWS CLI (if not installed)

```bash
# Check if AWS CLI is already installed
aws --version

# If not installed, install via Homebrew (macOS)
brew install awscli

# Verify installation
aws --version
# Expected output: aws-cli/2.x.x Python/3.x.x Darwin/...
```

---

### Step 2: Create AWS Access Keys

#### A. Log into AWS Console

1. Go to [AWS Console](https://console.aws.amazon.com/)
2. Sign in with your AWS account

#### B. Navigate to IAM (Identity and Access Management)

1. In the AWS Console search bar, type **"IAM"**
2. Click on **IAM** service

#### C. Create Access Keys

**Option 1: Create User (Recommended for deployment)**

1. Click **"Users"** in left sidebar
2. Click **"Create user"**
3. Enter username: `signum-deploy-user`
4. Click **"Next"**
5. Select **"Attach policies directly"**
6. Search and select these policies:
   - ✅ `AmazonEC2FullAccess`
   - ✅ `AmazonS3FullAccess`
   - ✅ `IAMReadOnlyAccess` (optional)
7. Click **"Next"** → **"Create user"**

**Option 2: Use Root User (Not Recommended for Production)**

1. Click your account name (top right)
2. Select **"Security Credentials"**
3. Scroll to **"Access keys"**

#### D. Generate Access Key

1. Click on the user you just created
2. Go to **"Security credentials"** tab
3. Scroll to **"Access keys"**
4. Click **"Create access key"**
5. Select use case: **"Command Line Interface (CLI)"**
6. Check the box: "I understand..."
7. Click **"Next"**
8. (Optional) Add description: "SIGNUM deployment key"
9. Click **"Create access key"**

#### E. Save Your Keys! 🔑

**IMPORTANT**: You'll see:
- **Access key ID**: `AKIAIOSFODNN7EXAMPLE` (20 characters)
- **Secret access key**: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` (40 characters)

**⚠️ WARNING**: The secret key is shown **ONLY ONCE**!

**Save them now**:
- Download CSV file (recommended)
- Copy to password manager
- Write them down temporarily

---

### Step 3: Configure AWS CLI

Open Terminal and run:

```bash
aws configure
```

You'll be prompted for 4 inputs:

```
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]: json
```

**Explanations**:
- **Access Key ID**: Paste the 20-character key you saved
- **Secret Access Key**: Paste the 40-character secret key
- **Region**: Choose based on your location:
  - `us-east-1` - US East (N. Virginia) - **Recommended for beginners**
  - `us-west-2` - US West (Oregon)
  - `eu-west-1` - Europe (Ireland)
  - `ap-southeast-1` - Asia Pacific (Singapore)
- **Output format**: `json` (recommended)

---

## ✅ Verify Configuration

### Test 1: Check Credentials

```bash
# View configured credentials (hides secret key)
aws configure list

# Expected output:
#       Name                    Value             Type    Location
#       ----                    -----             ----    --------
#    profile                <not set>             None    None
# access_key     ****************AMPLE shared-credentials-file
# secret_key     ****************AMPLE shared-credentials-file
#     region                us-east-1      config-file    ~/.aws/config
```

### Test 2: Verify AWS Access

```bash
# Get your AWS account identity
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "AIDAI...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/signum-deploy-user"
# }
```

### Test 3: List S3 Buckets

```bash
# List existing S3 buckets (may be empty)
aws s3 ls

# If you see a list or empty output (no errors), it works!
```

---

## 📂 Configuration Files Location

AWS CLI stores credentials in:

```bash
# Credentials file (contains access keys)
~/.aws/credentials

# Config file (contains region and settings)
~/.aws/config
```

### View Your Configuration Files

```bash
# View credentials
cat ~/.aws/credentials

# Output:
# [default]
# aws_access_key_id = AKIAIOSFODNN7EXAMPLE
# aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# View config
cat ~/.aws/config

# Output:
# [default]
# region = us-east-1
# output = json
```

---

## 🔄 Multiple Profiles (Optional)

If you want separate profiles for different projects:

```bash
# Configure additional profile
aws configure --profile signum-production

# Use specific profile
aws s3 ls --profile signum-production

# Set environment variable to use profile
export AWS_PROFILE=signum-production
```

---

## 🔐 Security Best Practices

### 1. Never Share Your Keys

- ❌ Don't commit to Git
- ❌ Don't share in emails/chat
- ❌ Don't hardcode in scripts
- ✅ Use IAM roles on EC2 (recommended)
- ✅ Use environment variables
- ✅ Rotate keys regularly

### 2. Add .aws to .gitignore

```bash
# Add to your .gitignore
echo ".aws/" >> ~/.gitignore
echo "*.pem" >> ~/.gitignore
```

### 3. Restrict IAM User Permissions

Only grant necessary permissions:
- For deployment: EC2, S3, CloudWatch
- Avoid: `AdministratorAccess` for deployment users

### 4. Enable MFA (Multi-Factor Authentication)

1. Go to IAM → Users → Your user
2. Security credentials tab
3. Click "Assign MFA device"
4. Follow wizard (use Google Authenticator app)

### 5. Rotate Access Keys Regularly

```bash
# Create new key (in AWS Console)
# Update configuration
aws configure

# Delete old key (in AWS Console)
```

---

## 🛠️ Troubleshooting

### Problem: "Unable to locate credentials"

**Solution**:
```bash
# Check if credentials file exists
ls -la ~/.aws/

# If missing, run configure again
aws configure
```

### Problem: "Access Denied" errors

**Solution**:
```bash
# Check your IAM user permissions in AWS Console
# Ensure user has policies:
# - AmazonEC2FullAccess
# - AmazonS3FullAccess

# Verify identity
aws sts get-caller-identity
```

### Problem: "Invalid credentials"

**Solution**:
```bash
# Keys might be expired or incorrect
# Regenerate keys in AWS Console
# Run configure again
aws configure
```

### Problem: Wrong region

**Solution**:
```bash
# Change default region
aws configure set region us-east-1

# Or specify region in commands
aws s3 ls --region us-east-1
```

---

## 🎯 Quick Commands Reference

```bash
# Configure AWS CLI
aws configure

# View current configuration
aws configure list

# Get account info
aws sts get-caller-identity

# List S3 buckets
aws s3 ls

# List EC2 instances
aws ec2 describe-instances --query 'Reservations[].Instances[].[InstanceId,State.Name,PublicIpAddress]' --output table

# Create S3 bucket
aws s3 mb s3://my-bucket-name --region us-east-1

# Upload file to S3
aws s3 cp myfile.txt s3://my-bucket-name/

# Download from S3
aws s3 cp s3://my-bucket-name/myfile.txt ./

# Sync directory to S3
aws s3 sync ./local-folder s3://my-bucket-name/remote-folder/

# Set specific region
aws configure set region us-west-2

# Set output format
aws configure set output json
```

---

## 📊 For SIGNUM Deployment

### Complete Setup Flow

```bash
# 1. Install AWS CLI
brew install awscli

# 2. Configure credentials
aws configure
# Enter: Access Key, Secret Key, us-east-1, json

# 3. Verify setup
aws sts get-caller-identity

# 4. Create S3 bucket for data
aws s3 mb s3://signum-hospital-data --region us-east-1

# 5. Upload hospital data
cd /Users/harshmaheshwari/development/Signum_1
aws s3 sync hospitals_current_data/ s3://signum-hospital-data/hospitals_current_data/

# 6. Verify upload
aws s3 ls s3://signum-hospital-data/hospitals_current_data/ --recursive --human-readable

# 7. You're ready to deploy! 🎉
```

---

## 🆘 Need Help?

### AWS Documentation
- [AWS CLI Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [AWS CLI Configure Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html)
- [IAM User Guide](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users.html)

### Common Issues
1. **Credentials not working**: Regenerate keys in AWS Console
2. **Region errors**: Use `us-east-1` for consistency
3. **Permission errors**: Check IAM policies attached to user

---

## ✅ Checklist

After completing this guide, you should have:

- [ ] AWS CLI installed (`aws --version` works)
- [ ] IAM user created (or using root - not recommended)
- [ ] Access keys generated and saved securely
- [ ] AWS CLI configured (`aws configure` completed)
- [ ] Configuration verified (`aws sts get-caller-identity` works)
- [ ] S3 access tested (`aws s3 ls` works)
- [ ] Keys saved in password manager
- [ ] .gitignore updated (optional)

---

## 🎉 You're Ready!

Once AWS CLI is configured, you can:
- ✅ Upload datasets to S3
- ✅ Launch EC2 instances
- ✅ Deploy SIGNUM API
- ✅ Use deployment scripts

**Next Steps**: 
- Read `QUICK_START_AWS.md` to deploy your API
- Run `deploy_ec2.sh` on your EC2 instance

---

*Last Updated: November 2025*
*Estimated Time: 10-15 minutes*
