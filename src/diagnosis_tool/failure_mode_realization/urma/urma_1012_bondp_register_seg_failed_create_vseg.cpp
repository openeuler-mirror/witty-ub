#include "urma_1012_bondp_register_seg_failed_create_vseg.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1012BondpRegisterSegFailedCreateVseg> g_urma("urma_1012");

bool Urma1012BondpRegisterSegFailedCreateVseg::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create vseg"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1012BondpRegisterSegFailedCreateVseg::GetName() const
{
    return "bondp_register_seg Failed to create vseg";
}

std::string Urma1012BondpRegisterSegFailedCreateVseg::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma1012BondpRegisterSegFailedCreateVseg::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1012BondpRegisterSegFailedCreateVseg::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1012BondpRegisterSegFailedCreateVseg::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create vseg";
}

std::string Urma1012BondpRegisterSegFailedCreateVseg::GetId() const
{
    return "urma_1012";
}
} // namespace diag
