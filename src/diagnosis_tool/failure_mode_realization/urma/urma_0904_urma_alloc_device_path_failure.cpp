#include "urma_0904_urma_alloc_device_path_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0904UrmaAllocDevicePathFailure> g_urma("urma_0904");

bool Urma0904UrmaAllocDevicePathFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"snprintf failed"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0904UrmaAllocDevicePathFailure::GetName() const
{
    return "urma_alloc_device 格式化路径失败";
}

std::string Urma0904UrmaAllocDevicePathFailure::GetRootCauseDesc() const
{
    return "路径或字符串处理失败，可能由于缓冲区长度不足、输入名称异常或系统调用返回错误；该路径返回 dev";
}

RootCause Urma0904UrmaAllocDevicePathFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0904UrmaAllocDevicePathFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0904UrmaAllocDevicePathFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：snprintf failed";
}

std::string Urma0904UrmaAllocDevicePathFailure::GetId() const
{
    return "urma_0904";
}
} // namespace diag
