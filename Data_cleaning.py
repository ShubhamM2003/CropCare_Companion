#!/usr/bin/env python
# coding: utf-8

# In[2]:


# Import Neccessary files
import string
import pandas as pd


# In[3]:


# Read CSV
df = pd.read_csv("Datasets/KCC.csv")


# In[4]:


df.describe()


# In[5]:


newdf = df[:1000]
newdf


# In[6]:


df = newdf
df


# In[7]:


df.describe()


# In[8]:


df.isnull().count()


# In[9]:


# Removing Punctuations From questions column
punctuations = string.punctuation
cols = df.columns
for c in cols:
    df[c] = df[c].str.strip()
    

    df['questions'] = df['questions'].str.replace(f"[{punctuations}]", "")
    


# In[10]:


df


# In[11]:


# Removing duplicate values
newdf =df.drop_duplicates(subset=['questions'])
df = newdf
newdf = df.drop_duplicates(subset=['answers'])


# In[12]:


df = newdf
df.describe()


# In[13]:


df


# In[14]:


# Removing ambiguous values

keys = ["details", "detail", "explained", "explaination", "explain", "transfer", "replied"]

df = df[~df.answers.str.contains('|'.join(keys))]


# In[15]:


df.describe()


# In[16]:


df['answers'].value_counts()


# In[17]:


newdf = df.sort_values(by=['answers'], axis=0)
df['answers']


# In[18]:


# #Write to file
# newdf.to_csv("Datasets/Farm_question_1.csv", index=False)


# In[19]:


df.isnull().count()


# Merging questions

# In[20]:


conv = pd.read_csv('Datasets/greetings.csv')


# In[21]:


conv


# In[22]:


final_q = pd.concat([conv, df])
final_q


# In[23]:


final_q.to_csv("Datasets/Final_PreProcessed_Dataset.csv", index=False)

