#include "urma_failure_452.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure452> g_urma("urma_452");

bool UrmaFailure452::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfc_batch") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure452::GetName() const
{
    return "jfc_arr、bad_jfc无效导致删除JFC失败";
}

std::string UrmaFailure452::GetRootCauseDesc() const
{
    return "urma_delete_jfc_batch用于删除JFC，调用方传入的jfc_arr、bad_jfc不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure452::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure452::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure452::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfc_batch，Invalid parameter.。";
}

std::string UrmaFailure452::GetId() const
{
    return "urma_452";
}
} // namespace diag
