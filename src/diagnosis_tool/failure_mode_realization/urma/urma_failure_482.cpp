#include "urma_failure_482.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure482> g_urma("urma_482");

bool UrmaFailure482::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty_check_jfc") != std::string::npos &&
           message.find("Invalid parameter, jfr cfg is null or jfc is NULL with non shared jfr flag.") !=
               std::string::npos;
}

std::string UrmaFailure482::GetName() const
{
    return "JFC无效导致创建Jetty、JFC失败";
}

std::string UrmaFailure482::GetRootCauseDesc() const
{
    return "urma_create_jetty_check_jfc用于创建Jetty、JFC，调用方传入的JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure482::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure482::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure482::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_jfc，Invalid parameter, jfr cfg is null or jfc "
           "is NULL"
           " with non shared jfr flag.。";
}

std::string UrmaFailure482::GetId() const
{
    return "urma_482";
}
} // namespace diag
