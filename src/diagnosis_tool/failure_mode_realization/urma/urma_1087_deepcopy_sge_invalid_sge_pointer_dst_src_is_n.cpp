#include "urma_1087_deepcopy_sge_invalid_sge_pointer_dst_src_is_n.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1087DeepcopySgeInvalidSgePointerDstSrcIsN> g_urma("urma_1087");

bool Urma1087DeepcopySgeInvalidSgePointerDstSrcIsN::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid sge pointer, dst or src is NULL."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1087DeepcopySgeInvalidSgePointerDstSrcIsN::GetName() const
{
    return "deepcopy_sge Invalid sge pointer, dst or src is N";
}

std::string Urma1087DeepcopySgeInvalidSgePointerDstSrcIsN::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `dst == NULL || src == NULL`；该路径返回 -1";
}

RootCause Urma1087DeepcopySgeInvalidSgePointerDstSrcIsN::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1087DeepcopySgeInvalidSgePointerDstSrcIsN::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1087DeepcopySgeInvalidSgePointerDstSrcIsN::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid sge pointer, dst or src is NULL.";
}

std::string Urma1087DeepcopySgeInvalidSgePointerDstSrcIsN::GetId() const
{
    return "urma_1087";
}
} // namespace diag
