#include "urma_1005_bondp_import_seg_failed_lookup_v2p_token_id_ret.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1005BondpImportSegFailedLookupV2pTokenIdRet> g_urma("urma_1005");

bool Urma1005BondpImportSegFailedLookupV2pTokenIdRet::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to lookup v2p_token_id, ret: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1005BondpImportSegFailedLookupV2pTokenIdRet::GetName() const
{
    return "bondp_import_seg Failed to lookup v2p_token_id, ret:";
}

std::string Urma1005BondpImportSegFailedLookupV2pTokenIdRet::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret != BONDP_HASH_MAP_NOT_FOUND_ERROR`；该路径返回 NULL";
}

RootCause Urma1005BondpImportSegFailedLookupV2pTokenIdRet::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1005BondpImportSegFailedLookupV2pTokenIdRet::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1005BondpImportSegFailedLookupV2pTokenIdRet::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to lookup v2p_token_id, ret: %.";
}

std::string Urma1005BondpImportSegFailedLookupV2pTokenIdRet::GetId() const
{
    return "urma_1005";
}
} // namespace diag
