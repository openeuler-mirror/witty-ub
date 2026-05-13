#include "urma_1206_deepcopy_sg_invalid_sg_pointer_dst_src_is_nu.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1206DeepcopySgInvalidSgPointerDstSrcIsNu> g_urma("urma_1206");

bool Urma1206DeepcopySgInvalidSgPointerDstSrcIsNu::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid sg pointer, dst or src is NULL."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1206DeepcopySgInvalidSgPointerDstSrcIsNu::GetName() const
{
    return "deepcopy_sg Invalid sg pointer, dst or src is NU";
}

std::string Urma1206DeepcopySgInvalidSgPointerDstSrcIsNu::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `dst == NULL || src == NULL`；该路径返回 -1";
}

RootCause Urma1206DeepcopySgInvalidSgPointerDstSrcIsNu::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1206DeepcopySgInvalidSgPointerDstSrcIsNu::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1206DeepcopySgInvalidSgPointerDstSrcIsNu::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid sg pointer, dst or src is NULL.";
}

std::string Urma1206DeepcopySgInvalidSgPointerDstSrcIsNu::GetId() const
{
    return "urma_1206";
}
} // namespace diag
