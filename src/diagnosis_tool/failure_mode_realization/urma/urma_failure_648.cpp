#include "urma_failure_648.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure648> g_urma("urma_648");

bool UrmaFailure648::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("read_eid_list_sysyf") != std::string::npos &&
           message.find("printf failed, eid idx:") != std::string::npos;
}

std::string UrmaFailure648::GetName() const
{
    return "读取EID、列表、sysyf执行失败导致读取EID、列表、sysyf失败";
}

std::string UrmaFailure648::GetRootCauseDesc() const
{
    return "read_eid_list_"
           "sysyf执行读取EID、列表、sysyf时依赖的读取EID、列表、sysyf步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure648::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure648::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure648::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：read_eid_list_sysyf，printf failed, eid idx:。";
}

std::string UrmaFailure648::GetId() const
{
    return "urma_648";
}
} // namespace diag
