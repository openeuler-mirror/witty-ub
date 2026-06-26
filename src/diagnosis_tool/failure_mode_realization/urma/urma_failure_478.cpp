#include "urma_failure_478.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure478> g_urma("urma_478");

bool UrmaFailure478::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfce") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure478::GetName() const
{
    return "JFCE无效导致删除JFCE失败";
}

std::string UrmaFailure478::GetRootCauseDesc() const
{
    return "urma_delete_jfce用于删除JFCE，调用方传入的JFCE不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure478::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure478::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure478::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfce，Invalid parameter.。";
}

std::string UrmaFailure478::GetId() const
{
    return "urma_478";
}
} // namespace diag
