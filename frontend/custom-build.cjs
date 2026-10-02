const fs = require('fs-extra');
const path = require('path');

const crmAppPath = path.resolve(__dirname, '../../crm/frontend');
const targetPath = path.resolve(__dirname);
const overrideSrcPath = path.resolve(__dirname, './src');
const overrideFilesPath = path.resolve(__dirname, './src_override');

// Files to copy from CRM frontend (excluding node_modules, vite.config.js which we have custom, and our override files)
const filesToCopy = [
    'index.html',
    'postcss.config.js',
    '.prettierrc.json',
    'public'
];

// Copy essential config files from CRM
console.log('Starting: Copying CRM config files...');
filesToCopy.forEach(file => {
    const srcFile = path.join(crmAppPath, file);
    const destFile = path.join(targetPath, file);

    if (fs.existsSync(srcFile)) {
        if (fs.statSync(srcFile).isDirectory()) {
            fs.copySync(srcFile, destFile, { overwrite: true });
        } else {
            fs.copyFileSync(srcFile, destFile);
        }
        console.log(`  Copied: ${file}`);
    } else {
        console.log(`  Skipped (not found): ${file}`);
    }
});
console.log('Completed: Copying config files.');

// Copy CRM src directory
console.log('Starting: Copying original CRM src...');
fs.copySync(path.join(crmAppPath, 'src'), overrideSrcPath, { overwrite: true });
console.log('Completed: Copying original src.');

// Apply our overrides
console.log('Starting: Applying overrides...');
if (fs.existsSync(overrideFilesPath)) {
    fs.copySync(overrideFilesPath, overrideSrcPath, { overwrite: true });
    console.log('Completed: Applying overrides.');
} else {
    console.log('Warning: No override files found at src_override/');
}

console.log('Build preparation complete.');
