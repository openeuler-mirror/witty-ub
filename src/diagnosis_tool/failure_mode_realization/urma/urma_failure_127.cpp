#include "urma_failure_127.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure127> g_urma("urma_127");

bool UrmaFailure127::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_tp_list") != std::string::npos &&
           message.find("Invalid parameter, trans_mode:") != std::string::npos;
}

std::string UrmaFailure127::GetName() const
{
    return "URMA context、配置参数、tp_cnt、tp_list无效导致获取TP列表失败";
}

std::string UrmaFailure127::GetRootCauseDesc() const
{
    return "urma_get_tp_list用于获取TP列表，调用方传入的URMA "
           "context、配置参数、tp_cnt、tp_list不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure127::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure127::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure127::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_tp_list，Invalid parameter, trans_mode:。";
}

std::string UrmaFailure127::GetId() const
{
    return "urma_127";
}
} // namespace diag
