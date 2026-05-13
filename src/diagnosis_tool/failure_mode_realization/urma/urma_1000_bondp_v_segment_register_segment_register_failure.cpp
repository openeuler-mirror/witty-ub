#include "urma_1000_bondp_v_segment_register_segment_register_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1000BondpVSegmentRegisterSegmentRegisterFailure> g_urma("urma_1000");

bool Urma1000BondpVSegmentRegisterSegmentRegisterFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Fail to register seg, ret:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1000BondpVSegmentRegisterSegmentRegisterFailure::GetName() const
{
    return "bondp_v_segment_register 注册Segment失败";
}

std::string Urma1000BondpVSegmentRegisterSegmentRegisterFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "ret";
}

RootCause Urma1000BondpVSegmentRegisterSegmentRegisterFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1000BondpVSegmentRegisterSegmentRegisterFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1000BondpVSegmentRegisterSegmentRegisterFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Fail to register seg, ret:%.";
}

std::string Urma1000BondpVSegmentRegisterSegmentRegisterFailure::GetId() const
{
    return "urma_1000";
}
} // namespace diag
