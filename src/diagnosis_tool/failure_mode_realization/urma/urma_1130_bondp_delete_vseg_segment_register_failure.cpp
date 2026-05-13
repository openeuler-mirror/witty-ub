#include "urma_1130_bondp_delete_vseg_segment_register_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1130BondpDeleteVsegSegmentRegisterFailure> g_urma("urma_1130");

bool Urma1130BondpDeleteVsegSegmentRegisterFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to unregister segment, token_id:%, handle:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1130BondpDeleteVsegSegmentRegisterFailure::GetName() const
{
    return "bondp_delete_vseg 注册Segment失败";
}

std::string Urma1130BondpDeleteVsegSegmentRegisterFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_FAIL";
}

RootCause Urma1130BondpDeleteVsegSegmentRegisterFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1130BondpDeleteVsegSegmentRegisterFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1130BondpDeleteVsegSegmentRegisterFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to unregister segment, token_id:%, handle:%.";
}

std::string Urma1130BondpDeleteVsegSegmentRegisterFailure::GetId() const
{
    return "urma_1130";
}
} // namespace diag
