#include "urma_0916_bondp_segment_get_args_list_invalid_param_va.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0916BondpSegmentGetArgsListInvalidParamVa> g_urma("urma_0916");

bool Urma0916BondpSegmentGetArgsListInvalidParamVa::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param va"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0916BondpSegmentGetArgsListInvalidParamVa::GetName() const
{
    return "bondp_segment_get_args_list Invalid param va";
}

std::string Urma0916BondpSegmentGetArgsListInvalidParamVa::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `(void*)cfg->va == NULL`；该路径返回 NULL";
}

RootCause Urma0916BondpSegmentGetArgsListInvalidParamVa::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0916BondpSegmentGetArgsListInvalidParamVa::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0916BondpSegmentGetArgsListInvalidParamVa::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param va";
}

std::string Urma0916BondpSegmentGetArgsListInvalidParamVa::GetId() const
{
    return "urma_0916";
}
} // namespace diag
