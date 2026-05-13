#include "urma_0061_urma_open_drivers_path_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0061UrmaOpenDriversPathFailure> g_urma("urma_0061");

bool Urma0061UrmaOpenDriversPathFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"snprintf_s % failed"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0061UrmaOpenDriversPathFailure::GetName() const
{
    return "urma_open_drivers 格式化路径失败";
}

std::string Urma0061UrmaOpenDriversPathFailure::GetRootCauseDesc() const
{
    return "路径或字符串处理失败，可能由于缓冲区长度不足、输入名称异常或系统调用返回错误";
}

RootCause Urma0061UrmaOpenDriversPathFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0061UrmaOpenDriversPathFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0061UrmaOpenDriversPathFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：snprintf_s % failed";
}

std::string Urma0061UrmaOpenDriversPathFailure::GetId() const
{
    return "urma_0061";
}
} // namespace diag
