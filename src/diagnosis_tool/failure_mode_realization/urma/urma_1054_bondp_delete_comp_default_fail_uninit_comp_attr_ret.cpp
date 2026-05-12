#include "urma_1054_bondp_delete_comp_default_fail_uninit_comp_attr_ret.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1054BondpDeleteCompDefaultFailUninitCompAttrRet> g_urma("urma_1054");

bool Urma1054BondpDeleteCompDefaultFailUninitCompAttrRet::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Fail to uninit comp attr, ret%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1054BondpDeleteCompDefaultFailUninitCompAttrRet::GetName() const
{
    return "bondp_delete_comp_default Fail to uninit comp attr, ret%.";
}

std::string Urma1054BondpDeleteCompDefaultFailUninitCompAttrRet::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `uninit_ret != 0`；该路径返回 delete_ret == URMA_SUCCESS ? uninit_ret";
}

RootCause Urma1054BondpDeleteCompDefaultFailUninitCompAttrRet::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1054BondpDeleteCompDefaultFailUninitCompAttrRet::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1054BondpDeleteCompDefaultFailUninitCompAttrRet::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Fail to uninit comp attr, ret%.";
}

std::string Urma1054BondpDeleteCompDefaultFailUninitCompAttrRet::GetId() const
{
    return "urma_1054";
}
} // namespace diag
