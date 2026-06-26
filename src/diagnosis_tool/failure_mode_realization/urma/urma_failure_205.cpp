#include "urma_failure_205.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure205> g_urma("urma_205");

bool UrmaFailure205::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure205::GetName() const
{
    return "JFR、JFC无效导致创建Jetty失败";
}

std::string UrmaFailure205::GetRootCauseDesc() const
{
    return "urma_create_jetty用于创建Jetty，调用方传入的JFR、JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure205::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure205::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure205::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty，Invalid parameter.。";
}

std::string UrmaFailure205::GetId() const
{
    return "urma_205";
}
} // namespace diag
