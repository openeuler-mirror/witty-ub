#include "urma_0319_deepcopy_jfr_wr_inner_failed_copy_wr_next.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0319DeepcopyJfrWrInnerFailedCopyWrNext> g_urma("urma_0319");

bool Urma0319DeepcopyJfrWrInnerFailedCopyWrNext::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to copy in wr->next"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0319DeepcopyJfrWrInnerFailedCopyWrNext::GetName() const
{
    return "deepcopy_jfr_wr_inner Failed to copy in wr->next";
}

std::string Urma0319DeepcopyJfrWrInnerFailedCopyWrNext::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `new_wr == NULL`；该路径返回 NULL";
}

RootCause Urma0319DeepcopyJfrWrInnerFailedCopyWrNext::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0319DeepcopyJfrWrInnerFailedCopyWrNext::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0319DeepcopyJfrWrInnerFailedCopyWrNext::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to copy in wr->next";
}

std::string Urma0319DeepcopyJfrWrInnerFailedCopyWrNext::GetId() const
{
    return "urma_0319";
}
} // namespace diag
