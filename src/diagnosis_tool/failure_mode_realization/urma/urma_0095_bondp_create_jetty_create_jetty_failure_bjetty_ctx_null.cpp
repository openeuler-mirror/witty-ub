#include "urma_0095_bondp_create_jetty_create_jetty_failure_bjetty_ctx_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0095BondpCreateJettyCreateJettyFailureBjettyCtxNull> g_urma("urma_0095");

bool Urma0095BondpCreateJettyCreateJettyFailureBjettyCtxNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create jetty ctx"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0095BondpCreateJettyCreateJettyFailureBjettyCtxNull::GetName() const
{
    return "bondp_create_jetty 创建Jetty失败（bjetty_ctx == NULL）";
}

std::string Urma0095BondpCreateJettyCreateJettyFailureBjettyCtxNull::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0095BondpCreateJettyCreateJettyFailureBjettyCtxNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0095BondpCreateJettyCreateJettyFailureBjettyCtxNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0095BondpCreateJettyCreateJettyFailureBjettyCtxNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create jetty ctx";
}

std::string Urma0095BondpCreateJettyCreateJettyFailureBjettyCtxNull::GetId() const
{
    return "urma_0095";
}
} // namespace diag
