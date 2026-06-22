#include "urma_failure_073.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure073> g_urma("urma_073");

bool UrmaFailure073::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_import_jfr_ex") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure073::GetName() const
{
    return "URMA context、dev_fd、tjfr、配置参数无效导致导入JFR失败";
}

std::string UrmaFailure073::GetRootCauseDesc() const
{
    return "urma_cmd_import_jfr_ex用于导入JFR，调用方传入的URMA "
           "context、dev_fd、tjfr、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure073::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure073::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure073::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_import_jfr_ex，Invalid parameter.。";
}

std::string UrmaFailure073::GetId() const
{
    return "urma_073";
}
} // namespace diag
