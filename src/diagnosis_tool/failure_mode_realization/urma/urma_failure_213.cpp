#include "urma_failure_213.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure213> g_urma("urma_213");

bool UrmaFailure213::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty_grp") != std::string::npos &&
           message.find("create_jetty_grp failed.") != std::string::npos;
}

std::string UrmaFailure213::GetName() const
{
    return "下层资源创建失败导致创建Jetty组失败";
}

std::string UrmaFailure213::GetRootCauseDesc() const
{
    return "urma_create_jetty_grp在创建Jetty组过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure213::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure213::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure213::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_grp，create_jetty_grp failed.。";
}

std::string UrmaFailure213::GetId() const
{
    return "urma_213";
}
} // namespace diag
