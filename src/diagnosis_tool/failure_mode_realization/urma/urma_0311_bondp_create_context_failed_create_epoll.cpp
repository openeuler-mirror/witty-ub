#include "urma_0311_bondp_create_context_failed_create_epoll.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0311BondpCreateContextFailedCreateEpoll> g_urma("urma_0311");

bool Urma0311BondpCreateContextFailedCreateEpoll::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create epoll %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0311BondpCreateContextFailedCreateEpoll::GetName() const
{
    return "bondp_create_context Failed to create epoll %";
}

std::string Urma0311BondpCreateContextFailedCreateEpoll::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0311BondpCreateContextFailedCreateEpoll::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0311BondpCreateContextFailedCreateEpoll::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0311BondpCreateContextFailedCreateEpoll::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create epoll %";
}

std::string Urma0311BondpCreateContextFailedCreateEpoll::GetId() const
{
    return "urma_0311";
}
} // namespace diag
