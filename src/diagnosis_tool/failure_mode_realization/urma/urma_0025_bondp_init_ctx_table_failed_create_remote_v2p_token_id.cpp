#include "urma_0025_bondp_init_ctx_table_failed_create_remote_v2p_token_id.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0025BondpInitCtxTableFailedCreateRemoteV2pTokenId> g_urma("urma_0025");

bool Urma0025BondpInitCtxTableFailedCreateRemoteV2pTokenId::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create remote_v2p_token_id_table"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0025BondpInitCtxTableFailedCreateRemoteV2pTokenId::GetName() const
{
    return "bondp_init_ctx_table Failed to create remote_v2p_token_id";
}

std::string Urma0025BondpInitCtxTableFailedCreateRemoteV2pTokenId::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "0";
}

RootCause Urma0025BondpInitCtxTableFailedCreateRemoteV2pTokenId::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0025BondpInitCtxTableFailedCreateRemoteV2pTokenId::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0025BondpInitCtxTableFailedCreateRemoteV2pTokenId::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create remote_v2p_token_id_table";
}

std::string Urma0025BondpInitCtxTableFailedCreateRemoteV2pTokenId::GetId() const
{
    return "urma_0025";
}
} // namespace diag
