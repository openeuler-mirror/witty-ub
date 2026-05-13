#include "urma_0313_bondp_create_pseg_invalid_segment_address_bondp_se.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0313BondpCreatePsegInvalidSegmentAddressBondpSe> g_urma("urma_0313");

bool Urma0313BondpCreatePsegInvalidSegmentAddressBondpSe::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid segment address for bondp seg"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0313BondpCreatePsegInvalidSegmentAddressBondpSe::GetName() const
{
    return "bondp_create_pseg Invalid segment address for bondp se";
}

std::string Urma0313BondpCreatePsegInvalidSegmentAddressBondpSe::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `(void *)seg_cfg->va ==NULL`；该路径返回 -1";
}

RootCause Urma0313BondpCreatePsegInvalidSegmentAddressBondpSe::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0313BondpCreatePsegInvalidSegmentAddressBondpSe::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0313BondpCreatePsegInvalidSegmentAddressBondpSe::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid segment address for bondp seg";
}

std::string Urma0313BondpCreatePsegInvalidSegmentAddressBondpSe::GetId() const
{
    return "urma_0313";
}
} // namespace diag
