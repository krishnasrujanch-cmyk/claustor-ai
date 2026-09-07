import { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = "https://claustor.com";
  const lastModified = new Date();

  return [
    { url: baseUrl, lastModified, changeFrequency: "weekly", priority: 1.0 },
    { url: `${baseUrl}/login`, lastModified, changeFrequency: "monthly", priority: 0.8 },
    { url: `${baseUrl}/contact`, lastModified, changeFrequency: "monthly", priority: 0.7 },
    { url: `${baseUrl}/privacy`, lastModified, changeFrequency: "monthly", priority: 0.3 },
    { url: `${baseUrl}/terms`, lastModified, changeFrequency: "monthly", priority: 0.3 },
    { url: `${baseUrl}/security`, lastModified, changeFrequency: "monthly", priority: 0.4 },
    { url: `${baseUrl}/forgot-password`, lastModified, changeFrequency: "monthly", priority: 0.2 },
  ];
}
