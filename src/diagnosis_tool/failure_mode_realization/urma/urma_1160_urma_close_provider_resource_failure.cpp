#include "urma_1160_urma_close_provider_resource_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1160UrmaCloseProviderResourceFailure> g_urma("urma_1160");

bool Urma1160UrmaCloseProviderResourceFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"% close failed, err: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1160UrmaCloseProviderResourceFailure::GetName() const
{
    return "urma_close_provider 关闭资源失败";
}

std::string Urma1160UrmaCloseProviderResourceFailure::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常";
}

RootCause Urma1160UrmaCloseProviderResourceFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1160UrmaCloseProviderResourceFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1160UrmaCloseProviderResourceFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：% close failed, err: %.";
}

std::string Urma1160UrmaCloseProviderResourceFailure::GetId() const
{
    return "urma_1160";
}
} // namespace diag
