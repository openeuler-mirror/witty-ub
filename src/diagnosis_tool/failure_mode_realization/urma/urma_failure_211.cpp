#include "urma_failure_211.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure211> g_urma("urma_211");

bool UrmaFailure211::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty_grp") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure211::GetName() const
{
    return "provider未提供ack_notify操作实现无效导致创建Jetty组失败";
}

std::string UrmaFailure211::GetRootCauseDesc() const
{
    return "urma_create_jetty_grp用于创建Jetty组，调用方传入的provider未提供ack_"
           "notify操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure211::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure211::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure211::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_grp，Invalid parameter.。";
}

std::string UrmaFailure211::GetId() const
{
    return "urma_211";
}
} // namespace diag
