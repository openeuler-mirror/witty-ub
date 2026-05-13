#include "urma_0023_bondp_init_ctx_table_failed_create_p_vjetty_id_table.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0023BondpInitCtxTableFailedCreatePVjettyIdTable> g_urma("urma_0023");

bool Urma0023BondpInitCtxTableFailedCreatePVjettyIdTable::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create p_vjetty_id_table"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0023BondpInitCtxTableFailedCreatePVjettyIdTable::GetName() const
{
    return "bondp_init_ctx_table Failed to create p_vjetty_id_table";
}

std::string Urma0023BondpInitCtxTableFailedCreatePVjettyIdTable::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0023BondpInitCtxTableFailedCreatePVjettyIdTable::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0023BondpInitCtxTableFailedCreatePVjettyIdTable::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0023BondpInitCtxTableFailedCreatePVjettyIdTable::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create p_vjetty_id_table";
}

std::string Urma0023BondpInitCtxTableFailedCreatePVjettyIdTable::GetId() const
{
    return "urma_0023";
}
} // namespace diag
