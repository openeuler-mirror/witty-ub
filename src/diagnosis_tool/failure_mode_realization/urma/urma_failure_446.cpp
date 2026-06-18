#include "urma_failure_446.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure446> g_urma("urma_446");

bool UrmaFailure446::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_modify_jfc") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure446::GetName() const
{
    return "JFC、属性参数无效导致修改JFC失败";
}

std::string UrmaFailure446::GetRootCauseDesc() const
{
    return "urma_modify_jfc用于修改JFC，调用方传入的JFC、属性参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure446::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure446::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure446::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_modify_jfc，Invalid parameter.。";
}

std::string UrmaFailure446::GetId() const
{
    return "urma_446";
}
} // namespace diag
