#include "urma_1176_urma_create_context_create_context_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1176UrmaCreateContextCreateContextFailure> g_urma("urma_1176");

bool Urma1176UrmaCreateContextCreateContextFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"[DRV_ERR]Failed to create urma context."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1176UrmaCreateContextCreateContextFailure::GetName() const
{
    return "urma_create_context 创建context失败";
}

std::string Urma1176UrmaCreateContextCreateContextFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 NULL";
}

RootCause Urma1176UrmaCreateContextCreateContextFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1176UrmaCreateContextCreateContextFailure::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string Urma1176UrmaCreateContextCreateContextFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Failed to create urma context.";
}

std::string Urma1176UrmaCreateContextCreateContextFailure::GetId() const
{
    return "urma_1176";
}
} // namespace diag
