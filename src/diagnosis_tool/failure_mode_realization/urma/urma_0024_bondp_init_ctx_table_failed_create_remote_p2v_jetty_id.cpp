#include "urma_0024_bondp_init_ctx_table_failed_create_remote_p2v_jetty_id.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0024BondpInitCtxTableFailedCreateRemoteP2vJettyId> g_urma("urma_0024");

bool Urma0024BondpInitCtxTableFailedCreateRemoteP2vJettyId::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create remote_p2v_jetty_id_table"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0024BondpInitCtxTableFailedCreateRemoteP2vJettyId::GetName() const
{
    return "bondp_init_ctx_table Failed to create remote_p2v_jetty_id";
}

std::string Urma0024BondpInitCtxTableFailedCreateRemoteP2vJettyId::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0024BondpInitCtxTableFailedCreateRemoteP2vJettyId::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0024BondpInitCtxTableFailedCreateRemoteP2vJettyId::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0024BondpInitCtxTableFailedCreateRemoteP2vJettyId::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create remote_p2v_jetty_id_table";
}

std::string Urma0024BondpInitCtxTableFailedCreateRemoteP2vJettyId::GetId() const
{
    return "urma_0024";
}
} // namespace diag
