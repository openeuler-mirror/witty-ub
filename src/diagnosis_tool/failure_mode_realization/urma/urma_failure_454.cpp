#include "urma_failure_454.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure454> g_urma("urma_454");

bool UrmaFailure454::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfc_batch") != std::string::npos &&
           message.find("Invalid parameter,") != std::string::npos &&
           message.find("jfc in the array is NULL.") != std::string::npos;
}

std::string UrmaFailure454::GetName() const
{
    return "jfce_arr无效导致删除JFC失败";
}

std::string UrmaFailure454::GetRootCauseDesc() const
{
    return "urma_delete_jfc_batch用于删除JFC，调用方传入的jfce_arr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure454::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure454::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure454::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfc_batch，Invalid parameter,，jfc in the array is NULL.。";
}

std::string UrmaFailure454::GetId() const
{
    return "urma_454";
}
} // namespace diag
