#include "urma_0333_deepcopy_jfs_wr_node_not_support_opcode.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0333DeepcopyJfsWrNodeNotSupportOpcode> g_urma("urma_0333");

bool Urma0333DeepcopyJfsWrNodeNotSupportOpcode::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Not support opcode %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0333DeepcopyJfsWrNodeNotSupportOpcode::GetName() const
{
    return "deepcopy_jfs_wr_node Not support opcode %";
}

std::string Urma0333DeepcopyJfsWrNodeNotSupportOpcode::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 "
           "new_wr";
}

RootCause Urma0333DeepcopyJfsWrNodeNotSupportOpcode::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0333DeepcopyJfsWrNodeNotSupportOpcode::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0333DeepcopyJfsWrNodeNotSupportOpcode::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Not support opcode %";
}

std::string Urma0333DeepcopyJfsWrNodeNotSupportOpcode::GetId() const
{
    return "urma_0333";
}
} // namespace diag
