#include "urma_0006_bondp_segment_uninit_comp_attr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0006BondpSegmentUninitCompAttrInvalidParam> g_urma("urma_0006");

bool Urma0006BondpSegmentUninitCompAttrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"invalid param."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0006BondpSegmentUninitCompAttrInvalidParam::GetName() const
{
    return "bondp_segment_uninit_comp_attr invalid param.";
}

std::string Urma0006BondpSegmentUninitCompAttrInvalidParam::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bdp_comp == NULL`；该路径返回 URMA_FAIL";
}

RootCause Urma0006BondpSegmentUninitCompAttrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0006BondpSegmentUninitCompAttrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0006BondpSegmentUninitCompAttrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：invalid param.";
}

std::string Urma0006BondpSegmentUninitCompAttrInvalidParam::GetId() const
{
    return "urma_0006";
}
} // namespace diag
