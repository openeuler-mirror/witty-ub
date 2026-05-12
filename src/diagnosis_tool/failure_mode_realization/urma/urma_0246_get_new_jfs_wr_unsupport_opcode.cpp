#include "urma_0246_get_new_jfs_wr_unsupport_opcode.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0246GetNewJfsWrUnsupportOpcode> g_urma("urma_0246");

bool Urma0246GetNewJfsWrUnsupportOpcode::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"unsupport opcode %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0246GetNewJfsWrUnsupportOpcode::GetName() const
{
    return "get_new_jfs_wr unsupport opcode %";
}

std::string Urma0246GetNewJfsWrUnsupportOpcode::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 "
           "new_wrs";
}

RootCause Urma0246GetNewJfsWrUnsupportOpcode::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0246GetNewJfsWrUnsupportOpcode::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0246GetNewJfsWrUnsupportOpcode::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：unsupport opcode %";
}

std::string Urma0246GetNewJfsWrUnsupportOpcode::GetId() const
{
    return "urma_0246";
}
} // namespace diag
