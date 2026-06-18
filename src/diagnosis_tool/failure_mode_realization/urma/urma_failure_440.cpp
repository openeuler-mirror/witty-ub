#include "urma_failure_440.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure440> g_urma("urma_440");

bool UrmaFailure440::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_wait_jfc") != std::string::npos &&
           message.find("Faile to wait jfc non-block, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure440::GetName() const
{
    return "WAIT、JFC执行失败导致WAIT、JFC失败";
}

std::string UrmaFailure440::GetRootCauseDesc() const
{
    return "urma_cmd_wait_jfc执行WAIT、JFC时依赖的WAIT、JFC步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure440::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure440::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure440::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_wait_jfc，Faile to wait jfc non-block, ret:，, errno:。";
}

std::string UrmaFailure440::GetId() const
{
    return "urma_440";
}
} // namespace diag
