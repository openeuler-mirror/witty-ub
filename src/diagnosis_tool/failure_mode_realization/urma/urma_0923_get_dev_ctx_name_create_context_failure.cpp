#include "urma_0923_get_dev_ctx_name_create_context_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0923GetDevCtxNameCreateContextFailure> g_urma("urma_0923");

bool Urma0923GetDevCtxNameCreateContextFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create context"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0923GetDevCtxNameCreateContextFailure::GetName() const
{
    return "get_dev_and_ctx_by_name 创建context失败";
}

std::string Urma0923GetDevCtxNameCreateContextFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0923GetDevCtxNameCreateContextFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0923GetDevCtxNameCreateContextFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0923GetDevCtxNameCreateContextFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create context";
}

std::string Urma0923GetDevCtxNameCreateContextFailure::GetId() const
{
    return "urma_0923";
}
} // namespace diag
