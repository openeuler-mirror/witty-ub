#include "urma_failure_707.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure707> g_urma("urma_707");

bool UrmaFailure707::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_modify_jfs") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure707::GetName() const
{
    return "JFS、属性参数无效导致修改JFS失败";
}

std::string UrmaFailure707::GetRootCauseDesc() const
{
    return "urma_modify_jfs用于修改JFS，调用方传入的JFS、属性参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure707::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure707::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure707::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_modify_jfs，Invalid parameter.。";
}

std::string UrmaFailure707::GetId() const
{
    return "urma_707";
}
} // namespace diag
