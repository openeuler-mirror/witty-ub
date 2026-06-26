#include "urma_failure_579.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure579> g_urma("urma_579");

bool UrmaFailure579::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfr_batch") != std::string::npos &&
           message.find("Invalid parameter, index:") != std::string::npos &&
           message.find("jfr in the array is NULL.") != std::string::npos;
}

std::string UrmaFailure579::GetName() const
{
    return "urma_ctx_arr无效导致删除JFR失败";
}

std::string UrmaFailure579::GetRootCauseDesc() const
{
    return "urma_delete_jfr_batch用于删除JFR，调用方传入的urma_ctx_arr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure579::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure579::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure579::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfr_batch，Invalid parameter, index:，jfr in the array is "
           "NULL.。";
}

std::string UrmaFailure579::GetId() const
{
    return "urma_579";
}
} // namespace diag
