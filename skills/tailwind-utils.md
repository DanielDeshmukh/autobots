---
name: tailwind-utils
description: Generic Tailwind CSS patterns for autobot-swarm. Use when building UI layouts, styling components, or creating responsive designs. Provides utility classes, spacing, typography, colors, and common patterns.
---

# Tailwind CSS Utilities Skill

## Container Patterns

```html
<!-- Centered container -->
<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

<!-- Card container -->
<div className="bg-white rounded-xl shadow-lg p-6">

<!-- Dark mode card -->
<div className="bg-gray-900 rounded-xl shadow-lg p-6 text-white">
```

## Layout Patterns

```html
<!-- Flex center -->
<div className="flex items-center justify-center">

<!-- Flex between -->
<div className="flex items-center justify-between">

<!-- Grid layout -->
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

<!-- Stack -->
<div className="flex flex-col space-y-4">
```

## Typography

```html
<!-- Heading -->
<h1 className="text-3xl font-bold text-gray-900">

<!-- Subheading -->
<h2 className="text-xl font-semibold text-gray-700">

<!-- Body text -->
<p className="text-gray-600 text-sm">

<!-- Small text -->
<span className="text-xs text-gray-500">
```

## Buttons

```html
<!-- Primary button -->
<button className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200">

<!-- Secondary button -->
<button className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium py-2 px-4 rounded-lg transition-colors duration-200">

<!-- Danger button -->
<button className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200">

<!-- Ghost button -->
<button className="text-blue-600 hover:text-blue-700 font-medium py-2 px-4 rounded-lg hover:bg-blue-50 transition-colors duration-200">
```

## Form Elements

```html
<!-- Input -->
<input
  type="text"
  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200"
/>

<!-- Select -->
<select className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200">

<!-- Textarea -->
<textarea className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200 resize-none">
```

## Spacing

```html
<!-- Margin -->
<div className="m-4">      <!-- All sides -->
<div className="mx-4">     <!-- Horizontal -->
<div className="my-4">     <!-- Vertical -->
<div className="mt-4">     <!-- Top only -->
<div className="mb-4">     <!-- Bottom only -->
<div className="ml-4">     <!-- Left only -->
<div className="mr-4">     <!-- Right only -->

<!-- Padding -->
<div className="p-4">      <!-- All sides -->
<div className="px-4">     <!-- Horizontal -->
<div className="py-4">     <!-- Vertical -->
```

## Colors

```html
<!-- Primary -->
<div className="bg-blue-600 text-white">

<!-- Success -->
<div className="bg-green-600 text-white">

<!-- Warning -->
<div className="bg-yellow-500 text-black">

<!-- Danger -->
<div className="bg-red-600 text-white">

<!-- Neutral -->
<div className="bg-gray-100 text-gray-900">
```

## Shadows

```html
<!-- Small shadow -->
<div className="shadow-sm">

<!-- Medium shadow -->
<div className="shadow-md">

<!-- Large shadow -->
<div className="shadow-lg">

<!-- Extra large shadow -->
<div className="shadow-xl">
```

## Border Radius

```html
<!-- Small radius -->
<div className="rounded-sm">

<!-- Medium radius -->
<div className="rounded-lg">

<!-- Large radius -->
<div className="rounded-xl">

<!-- Full radius (pill) -->
<div className="rounded-full">
```

## Responsive Design

```html
<!-- Mobile first -->
<div className="w-full md:w-1/2 lg:w-1/3">

<!-- Hide on mobile -->
<div className="hidden md:block">

<!-- Show only on mobile -->
<div className="block md:hidden">
```

## Animations

```html
<!-- Transition -->
<div className="transition-all duration-200 ease-in-out">

<!-- Hover scale -->
<div className="hover:scale-105 transition-transform duration-200">

<!-- Fade in -->
<div className="animate-fade-in">
```

## Dark Mode

```html
<!-- Dark mode background -->
<div className="bg-white dark:bg-gray-900">

<!-- Dark mode text -->
<div className="text-gray-900 dark:text-white">

<!-- Dark mode border -->
<div className="border-gray-200 dark:border-gray-700">
```

## Best Practices

1. Use mobile-first responsive design
2. Keep consistent spacing throughout
3. Use semantic color names
4. Add transitions for interactive elements
5. Use dark mode variants for themes
6. Keep utility classes organized
7. Use custom CSS for complex animations
8. Test on different screen sizes
