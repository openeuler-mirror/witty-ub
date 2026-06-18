#include "urma_failure_553.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure553> g_urma("urma_553");

bool UrmaFailure553::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jetty_batch") != std::string::npos &&
           message.find("bad jetty index exceed array length, bad_jetty_index:") != std::string::npos;
}

std::string UrmaFailure553::GetName() const
{
    return "Jetty状态不满足要求导致删除Jetty失败";
}

std::string UrmaFailure553::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jetty_batch执行删除Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure553::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure553::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure553::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jetty_batch，bad jetty index exceed array length, "
           "bad_jetty_in"
           "dex:。";
}

std::string UrmaFailure553::GetId() const
{
    return "urma_553";
}
} // namespace diag
