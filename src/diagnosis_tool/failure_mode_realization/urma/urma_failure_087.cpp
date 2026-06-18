#include "urma_failure_087.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure087> g_urma("urma_087");

bool UrmaFailure087::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_tp_list") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure087::GetName() const
{
    return "URMA context、dev_fd、配置参数、tp_cnt无效导致获取TP列表失败";
}

std::string UrmaFailure087::GetRootCauseDesc() const
{
    return "urma_cmd_get_tp_list用于获取TP列表，调用方传入的URMA "
           "context、dev_fd、配置参数、tp_cnt不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure087::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure087::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure087::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_tp_list，Invalid parameter.。";
}

std::string UrmaFailure087::GetId() const
{
    return "urma_087";
}
} // namespace diag
