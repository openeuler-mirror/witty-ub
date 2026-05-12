#include "urma_0007_bondp_segment_uninit_comp_attr_segment_register_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0007BondpSegmentUninitCompAttrSegmentRegisterFailure> g_urma("urma_0007");

bool Urma0007BondpSegmentUninitCompAttrSegmentRegisterFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to unregister segment, token_id:%, handle:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0007BondpSegmentUninitCompAttrSegmentRegisterFailure::GetName() const
{
    return "bondp_segment_uninit_comp_attr 注册Segment失败";
}

std::string Urma0007BondpSegmentUninitCompAttrSegmentRegisterFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_FAIL";
}

RootCause Urma0007BondpSegmentUninitCompAttrSegmentRegisterFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0007BondpSegmentUninitCompAttrSegmentRegisterFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0007BondpSegmentUninitCompAttrSegmentRegisterFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to unregister segment, token_id:%, handle:%.";
}

std::string Urma0007BondpSegmentUninitCompAttrSegmentRegisterFailure::GetId() const
{
    return "urma_0007";
}
} // namespace diag
