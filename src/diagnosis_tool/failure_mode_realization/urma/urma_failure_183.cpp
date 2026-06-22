#include "urma_failure_183.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure183> g_urma("urma_183");

bool UrmaFailure183::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_alloc_jetty") != std::string::npos &&
           message.find("failed to fill jetty cfg") != std::string::npos;
}

std::string UrmaFailure183::GetName() const
{
    return "分配Jetty执行失败导致分配Jetty失败";
}

std::string UrmaFailure183::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_jetty执行分配Jetty时依赖的分配Jetty步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure183::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure183::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure183::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_jetty，failed to fill jetty cfg。";
}

std::string UrmaFailure183::GetId() const
{
    return "urma_183";
}
} // namespace diag
