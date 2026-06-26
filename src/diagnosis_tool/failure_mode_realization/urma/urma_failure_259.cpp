#include "urma_failure_259.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure259> g_urma("urma_259");

bool UrmaFailure259::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jetty_grp") != std::string::npos &&
           message.find("Invalid parameter: jetty_list") != std::string::npos;
}

std::string UrmaFailure259::GetName() const
{
    return "provider未提供delete_jetty_grp操作实现无效导致删除Jetty组失败";
}

std::string UrmaFailure259::GetRootCauseDesc() const
{
    return "urma_delete_jetty_grp用于删除Jetty组，调用方传入的provider未提供delete_jetty_"
           "grp操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure259::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure259::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure259::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty_grp，Invalid parameter: jetty_list。";
}

std::string UrmaFailure259::GetId() const
{
    return "urma_259";
}
} // namespace diag
