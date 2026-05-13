#include "urma_1011_bondp_register_seg_failed_create_pseg.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1011BondpRegisterSegFailedCreatePseg> g_urma("urma_1011");

bool Urma1011BondpRegisterSegFailedCreatePseg::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create pseg"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1011BondpRegisterSegFailedCreatePseg::GetName() const
{
    return "bondp_register_seg Failed to create pseg";
}

std::string Urma1011BondpRegisterSegFailedCreatePseg::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma1011BondpRegisterSegFailedCreatePseg::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1011BondpRegisterSegFailedCreatePseg::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1011BondpRegisterSegFailedCreatePseg::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create pseg";
}

std::string Urma1011BondpRegisterSegFailedCreatePseg::GetId() const
{
    return "urma_1011";
}
} // namespace diag
