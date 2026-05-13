#include "urma_1009_bondp_register_seg_invalid_token_id_register_bondp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1009BondpRegisterSegInvalidTokenIdRegisterBondp> g_urma("urma_1009");

bool Urma1009BondpRegisterSegInvalidTokenIdRegisterBondp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid token id for register bondp seg"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1009BondpRegisterSegInvalidTokenIdRegisterBondp::GetName() const
{
    return "bondp_register_seg Invalid token id for register bondp";
}

std::string Urma1009BondpRegisterSegInvalidTokenIdRegisterBondp::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma1009BondpRegisterSegInvalidTokenIdRegisterBondp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1009BondpRegisterSegInvalidTokenIdRegisterBondp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1009BondpRegisterSegInvalidTokenIdRegisterBondp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid token id for register bondp seg";
}

std::string Urma1009BondpRegisterSegInvalidTokenIdRegisterBondp::GetId() const
{
    return "urma_1009";
}
} // namespace diag
