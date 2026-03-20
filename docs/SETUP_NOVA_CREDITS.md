# How to Get Nova 2 Lite Working — Credits & Setup

Guide to pay for and use Amazon Nova 2 Lite for the hackathon.

---

## 1. Create or Use an AWS Account

1. Go to [aws.amazon.com](https://aws.amazon.com)
2. **Create account** (or sign in if you have one)
3. Add a **payment method** (credit card) — required for Bedrock
4. New accounts get **12 months free tier** + **$200 credits** for 90 days (varies by region/promo)

---

## 2. Enable Nova 2 Lite in Bedrock

**Amazon models (Nova) are enabled by default** — pas d’abonnement manuel. Il faut juste un moyen de paiement valide.

1. Ouvre la [console Amazon Bedrock](https://console.aws.amazon.com/bedrock/)
2. Choisis la région **US East (N. Virginia)** — `us-east-1` (en haut à droite)
3. Va dans **Model access** (sous Bedrock configurations) — la page peut afficher "Model access has been retired" : c’est normal, l’accès est désormais automatique
4. Va dans **Playgrounds** → **Chat / Text** → sélectionne un modèle Nova 2 et teste

**Note :** Le premier appel peut déclencher une mise en place (jusqu’à 15 min). Si tu vois `AccessDeniedException`, attends quelques minutes et réessaie. Si tu vois `Operation not allowed`, voir section 7.1.

---

## 3. Get Credentials for Your Code

### Option A: IAM User (classic)

1. **IAM** → **Users** → **Create user**
2. Attach policy: `AmazonBedrockFullAccess` (or a custom policy with `bedrock:InvokeModel`)
3. **Security credentials** → **Create access key**
4. Dans `naviguide_workspace/.env`, ajoute aussi `ANTHROPIC_API_KEY` (clé depuis [console.anthropic.com](https://console.anthropic.com)) pour le fallback quand Bedrock est bloqué.
5. Set environment variables:
   ```bash
   export AWS_ACCESS_KEY_ID=AKIA...
   export AWS_SECRET_ACCESS_KEY=...
   export AWS_DEFAULT_REGION=us-east-1
   ```

### Option B: Bedrock API Keys (simpler)

1. [Bedrock Console](https://console.aws.amazon.com/bedrock/) → **API keys** (left menu)
2. **Generate long-term API key**
3. Set expiration (e.g. 30 days for the hackathon)
4. Copy the key
5. **Où mettre la clé** — créer `naviguide_workspace/.env` :
   ```bash
   # naviguide_workspace/.env
   AWS_BEARER_TOKEN_BEDROCK=ta_clé_bedrock
   # Fallback quand Bedrock bloqué : clé API Anthropic (console.anthropic.com)
   ANTHROPIC_API_KEY=sk-ant-...
   ```
   Ou en variable d'environnement avant de lancer :
   ```bash
   export AWS_BEARER_TOKEN_BEDROCK=your_api_key_here
   export ANTHROPIC_API_KEY=sk-ant-...   # fallback direct Claude
   ./naviguide_workspace/start_local.sh
   ```

**Reference:** [Accelerate AI development with Amazon Bedrock API keys](https://aws.amazon.com/blogs/machine-learning/accelerate-ai-development-with-amazon-bedrock-api-keys/)

---

## 4. Nova 2 Lite Pricing (very cheap)

| | Price |
|---|-------|
| **Input tokens** | ~$0.30 per 1M tokens |
| **Output tokens** | ~$2.50 per 1M tokens |

**Example:** One briefing = ~2K input + ~500 output tokens ≈ **$0.001** (0.1 cent)

For the hackathon (dozens of tests + demo): **under $1 total**.

---

## 5. Verify It Works

```bash
# With IAM credentials or API key set (us-east-1 = US region → use us. prefix)
python3 -c "
import boto3
client = boto3.client('bedrock-runtime', region_name='us-east-1')
r = client.converse(
    modelId='us.amazon.nova-2-lite-v1:0',
    messages=[{'role': 'user', 'content': [{'text': 'Say hello in one word'}]}]
)
print(r['output']['message']['content'][0]['text'])
"
```

If you see a response, Nova is working.

---

## 6. Hackathon Resources (from Devpost)

| Resource | URL |
|----------|-----|
| **Nova Code Examples** | https://docs.aws.amazon.com/nova/latest/userguide/code-examples.html |
| **Nova 2 Lite Blog** | https://aws.amazon.com/blogs/aws/introducing-amazon-nova-2-lite-a-fast-cost-effective-reasoning-model/ |
| **Bedrock API Keys** | https://aws.amazon.com/blogs/machine-learning/accelerate-ai-development-with-amazon-bedrock-api-keys/ |
| **Office Hours** | Wed 8:00am PT — [Resources](https://amazon-nova.devpost.com/resources) |
| **Discord** | #tech-questions for support |

---

## 7. Troubleshooting

| Error | Fix |
|------|-----|
| **`ValidationException: Operation not allowed`** | **→ Restrictions compte ou vérification en cours.** Voir section 7.1 ci-dessous. |
| `AccessDeniedException` | Wait 2–15 min after first use; check IAM/API key permissions |
| `ValidationException` (autre) | Verify model ID: `us.amazon.nova-2-lite-v1:0` (US) ou `amazon.nova-2-lite-v1:0` |
| `ExpiredToken` | Refresh API key or IAM credentials |
| No payment method | Add a card in **Billing** → **Payment methods** |

### 7.1 "Operation not allowed" — Recherche approfondie (doc AWS/Bedrock)

D’après la doc officielle et les cas re:Post, cette erreur peut persister **même avec compte payant** et permissions correctes. Causes identifiées :

#### Diagnostic rapide

```bash
# Vérifier le statut d'autorisation du modèle
aws bedrock get-foundation-model-availability --model-id us.amazon.nova-2-lite-v1:0 --region us-east-1
```

Si tu vois `"authorizationStatus": "NOT_AUTHORIZED"` alors que `agreementAvailability` et `regionAvailability` sont `AVAILABLE`, c’est une **restriction au niveau du compte**, pas des permissions IAM.

#### Dans la console Bedrock

- Si le Playground affiche **"Your account verification is in progress"** → la vérification Bedrock est en cours côté AWS (peut prendre plusieurs jours sur les comptes récents).

#### Pistes à essayer (dans l’ordre)

1. **Credentials IAM** — crée un IAM user avec `AmazonBedrockFullAccess`, génère une access key, et mets dans `.env` :
   ```
   AWS_ACCESS_KEY_ID=AKIA...
   AWS_SECRET_ACCESS_KEY=...
   AWS_DEFAULT_REGION=us-east-1
   ```
   (Retire ou commente `AWS_BEARER_TOKEN_BEDROCK` pour forcer l’usage IAM)

2. **Région** — utilise **us-east-1** (US East N. Virginia). Pour Nova 2 en US, le model ID doit être `us.amazon.nova-2-lite-v1:0`.

3. **Compte root** — teste en te connectant avec le **compte root** (pas un IAM user) pour écarter les problèmes de délégation.

4. **AWS Organizations** — si ton compte est dans une Organisation, vérifie qu’aucune **SCP** ne bloque `aws-marketplace:Subscribe` ou les actions Bedrock.

5. **Modèles Anthropic (Claude)** — pour Claude, les premiers utilisateurs doivent soumettre un **formulaire use case** une fois dans la console Bedrock (Model access → sélectionner un modèle Anthropic → Submit use case details).

6. **Pays / adresse de facturation** — pour Anthropic, l’adresse de facturation doit être dans un [pays supporté](https://www.anthropic.com/supported-countries). Nova n’a pas cette contrainte.

#### Solution recommandée : Support AWS

Si tout échoue, **ouvre un cas AWS Support** :

- **Catégorie** : **Account and billing** (gratuit, sans plan support)
- **URL** : [https://console.aws.amazon.com/support](https://console.aws.amazon.com/support)
- **À préciser** : "ValidationException: Operation not allowed" sur Bedrock, même avec compte payant, IAM correct, région us-east-1. Joindre le résultat de `get-foundation-model-availability` si possible.

Les experts AWS indiquent que certaines restrictions sont liées à des **processus internes de vérification** non documentés. Un cas "Account and billing" est la voie officielle pour débloquer l’accès.

#### Références

- [Access Amazon Bedrock foundation models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)
- [Resolve validation exceptions](https://repost.aws/knowledge-center/bedrock-validation-exception-errors)
- [Enable Anthropic Claude models](https://repost.aws/knowledge-center/bedrock-access-anthropic-model)
- [Automatic enablement (Oct 2025)](https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-automatic-enablement-serverless-foundation-models/)

---

*For NAVIGUIDE: once credentials are in `naviguide_workspace/.env`, the orchestrator loads them at startup. Nova 2 Lite is tried first; Claude 3.5 Sonnet is the fallback if Nova fails.*
