#include "urma_1184_bondp_user_ctl_unsupported_opcode.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1184BondpUserCtlUnsupportedOpcode> g_urma("urma_1184");

bool Urma1184BondpUserCtlUnsupportedOpcode::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Unsupported opcode, opcode:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1184BondpUserCtlUnsupportedOpcode::GetName() const
{
    return "bondp_user_ctl Unsupported opcode, opcode:%";
}

std::string Urma1184BondpUserCtlUnsupportedOpcode::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 "
           "-EINVAL";
}

RootCause Urma1184BondpUserCtlUnsupportedOpcode::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1184BondpUserCtlUnsupportedOpcode::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1184BondpUserCtlUnsupportedOpcode::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Unsupported opcode, opcode:%";
}

std::string Urma1184BondpUserCtlUnsupportedOpcode::GetId() const
{
    return "urma_1184";
}
} // namespace diag
