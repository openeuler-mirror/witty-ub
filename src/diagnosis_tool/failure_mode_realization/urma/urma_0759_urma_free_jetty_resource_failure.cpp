#include "urma_0759_urma_free_jetty_resource_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0759UrmaFreeJettyResourceFailure> g_urma("urma_0759");

bool Urma0759UrmaFreeJettyResourceFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jetty still actived, please deactived first"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0759UrmaFreeJettyResourceFailure::GetName() const
{
    return "urma_free_jetty 激活资源失败";
}

std::string Urma0759UrmaFreeJettyResourceFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0759UrmaFreeJettyResourceFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0759UrmaFreeJettyResourceFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0759UrmaFreeJettyResourceFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jetty still actived, please deactived first";
}

std::string Urma0759UrmaFreeJettyResourceFailure::GetId() const
{
    return "urma_0759";
}
} // namespace diag
