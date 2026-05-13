#include "urma_0325_deepcopy_jfs_wr_inner_failed_copy_wr_next.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0325DeepcopyJfsWrInnerFailedCopyWrNext> g_urma("urma_0325");

bool Urma0325DeepcopyJfsWrInnerFailedCopyWrNext::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to copy in wr->next"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0325DeepcopyJfsWrInnerFailedCopyWrNext::GetName() const
{
    return "deepcopy_jfs_wr_inner Failed to copy in wr->next";
}

std::string Urma0325DeepcopyJfsWrInnerFailedCopyWrNext::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `new_wr == NULL`；该路径返回 NULL";
}

RootCause Urma0325DeepcopyJfsWrInnerFailedCopyWrNext::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0325DeepcopyJfsWrInnerFailedCopyWrNext::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0325DeepcopyJfsWrInnerFailedCopyWrNext::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to copy in wr->next";
}

std::string Urma0325DeepcopyJfsWrInnerFailedCopyWrNext::GetId() const
{
    return "urma_0325";
}
} // namespace diag
